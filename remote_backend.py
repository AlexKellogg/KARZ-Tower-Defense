from dataclasses import asdict

import httpx

from backend import LEADERBOARD_SIZE, AccessDenied, Account, AccountError, AccountSummary, Backend, LeaderboardEntry

OFFLINE = "Can't reach the KARZ server. Check your connection and try again."


class RemoteBackend(Backend):
    def __init__(self, base_url, client=None, timeout=8.0):
        self.base_url = base_url.rstrip('/')
        self.client = client or httpx.Client(base_url=self.base_url, timeout=timeout)
        self.tokens = {}

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
                raise AccountError('Please log in again.')
            headers['Authorization'] = f'Bearer {token}'
        try:
            response = self.client.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError:
            raise AccountError(OFFLINE) from None
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
        if kind == 'value':
            raise ValueError(detail)
        raise AccountError(detail)

    def _start_session(self, data):
        account = Account(**data['account'])
        self.tokens[account.id] = data['token']
        return account

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
        return tuple(self._call('GET', '/me/unlocked', account)['difficulties'])

    def record_run(self, account, result):
        return tuple(self._call('POST', '/me/runs', account, json=asdict(result))['unlocked'])

    def leaderboard(self, kind, difficulty=None, limit=LEADERBOARD_SIZE):
        params = {'limit': limit}
        if difficulty is not None:
            params['difficulty'] = difficulty
        return [LeaderboardEntry(**row) for row in self._call('GET', f'/leaderboard/{kind}', params=params)]

    def list_accounts(self, requester):
        return [AccountSummary(Account(**row['account']), tuple(row['unlocked']), row['best_score'],
                               row['games_played'], row['joined'])
                for row in self._call('GET', '/admin/accounts', requester)]

    def set_role(self, requester, account_id, role):
        return Account(**self._call('PUT', f'/admin/accounts/{account_id}/role', requester, json={'role': role}))
