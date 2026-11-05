import json
from dataclasses import asdict
from pathlib import Path

import httpx

from backend import (LEADERBOARD_SIZE, AccessDenied, Account, AccountError, AccountSummary, Backend,
                     LeaderboardEntry, RunResult, ScoreQueued)

OFFLINE = "Can't reach the KARZ server. Check your connection and try again."
QUEUED = 'Server unreachable. Your score is saved on this computer and will upload when you are back online.'
EXPIRED = 'Your login expired. Your score is saved on this computer and will upload next time you log in.'
DEFAULT_PENDING = Path.home()/'.karz_td'/'pending_runs.json'


class Offline(AccountError):
    pass


class NotLoggedIn(AccountError):
    pass


class RemoteBackend(Backend):
    def __init__(self, base_url, client=None, timeout=8.0, pending_path=DEFAULT_PENDING):
        self.base_url = base_url.rstrip('/')
        self.client = client or httpx.Client(base_url=self.base_url, timeout=timeout)
        self.tokens = {}
        self.pending_path = Path(pending_path)

    def close(self):
        for token in list(self.tokens.values()):
            try:
                self.client.post('/auth/logout', headers={'Authorization': f'Bearer {token}'})
            except httpx.HTTPError:
                pass
        self.tokens.clear()
        self.client.close()

    def _call(self, method, path, account=None, **kwargs):
        headers = {}
        if account is not None:
            token = self.tokens.get(account.id)
            if token is None:
                raise NotLoggedIn('Please log in again.')
            headers['Authorization'] = f'Bearer {token}'
        try:
            response = self.client.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError:
            raise Offline(OFFLINE) from None
        if response.status_code < 400:
            return response.json()
        try:
            body = response.json()
        except ValueError:
            body = {}
        detail = body.get('detail') if isinstance(body, dict) else None
        if not isinstance(detail, str):
            detail = f'Server error ({response.status_code}). Try again later.'
        kind = body.get('error') if isinstance(body, dict) else None
        if response.status_code == 403:
            raise AccessDenied(detail)
        if response.status_code == 401 and account is not None:
            self.tokens.pop(account.id, None)
            raise NotLoggedIn(detail)
        if kind == 'value':
            raise ValueError(detail)
        raise AccountError(detail)

    def _start_session(self, data):
        account = Account(**data['account'])
        self.tokens[account.id] = data['token']
        self._flush(account)
        return account

    def _load_pending(self):
        try:
            entries = json.loads(self.pending_path.read_text())
        except (OSError, ValueError):
            return []
        return entries if isinstance(entries, list) else []

    def _save_pending(self, entries):
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.pending_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(entries, indent=1))
        tmp.replace(self.pending_path)

    def _mine(self, entry, account):
        return entry.get('server') == self.base_url and entry.get('account_id') == account.id

    def pending_runs(self, account):
        return [RunResult(**e['result']) for e in self._load_pending()
                if self._mine(e, account) and e.get('kind', 'run') == 'run']

    def pending_checkpoints(self, account):
        return [e for e in self._load_pending() if self._mine(e, account) and e.get('kind') in ('checkpoint', 'clear')]

    def _queue(self, account, entry):
        self._save_pending(self._load_pending()+[{'server': self.base_url, 'account_id': account.id, **entry}])

    def _send(self, account, entry):
        kind = entry.get('kind', 'run')
        if kind == 'run':
            return self._call('POST', '/me/runs', account, json=entry['result'])['unlocked']
        path = f"/me/checkpoints/{entry['difficulty']}/{entry['mode']}"
        if kind == 'checkpoint':
            self._call('PUT', path, account, json={'state': entry['state']})
        else:
            self._call('DELETE', path, account)
        return []

    def _flush(self, account):
        entries = self._load_pending()
        if not any(self._mine(e, account) for e in entries):
            return ()
        unlocked, keep = [], []
        for i, entry in enumerate(entries):
            if not self._mine(entry, account):
                keep.append(entry)
                continue
            try:
                unlocked += self._send(account, entry)
            except (Offline, NotLoggedIn):
                keep.extend(entries[i:])
                break
            except (AccountError, AccessDenied, ValueError):
                continue
        self._save_pending(keep)
        return tuple(unlocked)

    def sign_up(self, name, username, email, password):
        return self._start_session(self._call('POST', '/auth/signup', json={
            'name': name, 'username': username, 'email': email, 'password': password}))

    def log_in(self, email, password):
        return self._start_session(self._call('POST', '/auth/login', json={'email': email, 'password': password}))

    def log_out(self, account):
        token = self.tokens.pop(account.id, None)
        if token is None:
            return
        try:
            self.client.post('/auth/logout', headers={'Authorization': f'Bearer {token}'})
        except httpx.HTTPError:
            pass

    def update_account(self, account, current_password, name, username, email, new_password=''):
        return Account(**self._call('PUT', '/me', account, json={
            'current_password': current_password, 'name': name, 'username': username, 'email': email,
            'new_password': new_password}))

    def unlocked_difficulties(self, account):
        self._flush(account)
        return tuple(self._call('GET', '/me/unlocked', account)['difficulties'])

    def record_run(self, account, result):
        earlier = self._flush(account)
        try:
            return earlier+tuple(self._call('POST', '/me/runs', account, json=asdict(result))['unlocked'])
        except (Offline, NotLoggedIn) as e:
            self._save_pending(self._load_pending()+[
                {'server': self.base_url, 'account_id': account.id, 'result': asdict(result)}])
            raise ScoreQueued(QUEUED if isinstance(e, Offline) else EXPIRED) from None

    def leaderboard(self, kind, difficulty=None, limit=LEADERBOARD_SIZE, mode='regular'):
        params = {'limit': limit, 'mode': mode}
        if difficulty is not None:
            params['difficulty'] = difficulty
        return [LeaderboardEntry(**row) for row in self._call('GET', f'/leaderboard/{kind}', params=params)]

    def list_accounts(self, requester):
        return [AccountSummary(Account(**row['account']), tuple(row['unlocked']), row['best_score'],
                               row['games_played'], row['joined'])
                for row in self._call('GET', '/admin/accounts', requester)]

    def set_role(self, requester, account_id, role):
        return Account(**self._call('PUT', f'/admin/accounts/{account_id}/role', requester, json={'role': role}))

    def _send_or_queue(self, account, entry):
        if any(self._mine(e, account) for e in self._load_pending()):
            self._queue(account, entry)
            self._flush(account)
            return
        try:
            self._send(account, entry)
        except (Offline, NotLoggedIn):
            self._queue(account, entry)

    def save_checkpoint(self, account, difficulty, mode, state):
        self._send_or_queue(account, {'kind': 'checkpoint', 'difficulty': difficulty, 'mode': mode, 'state': state})

    def load_checkpoint(self, account, difficulty, mode):
        self._flush(account)
        return self._call('GET', f'/me/checkpoints/{difficulty}/{mode}', account)['state']

    def clear_checkpoint(self, account, difficulty, mode):
        self._send_or_queue(account, {'kind': 'clear', 'difficulty': difficulty, 'mode': mode})
