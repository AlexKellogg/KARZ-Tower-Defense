import os
from dataclasses import asdict
from typing import Optional

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend import LEADERBOARD_SIZE, AccessDenied, AccountError, RunResult
from server.sql_backend import DEFAULT_URL, SqlBackend


class SignUpBody(BaseModel):
    name: str = Field(max_length=100)
    username: str = Field(max_length=40)
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class LogInBody(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class UpdateBody(BaseModel):
    current_password: str = Field(max_length=200)
    name: str = Field(max_length=100)
    username: str = Field(max_length=40)
    email: str = Field(max_length=254)
    new_password: str = Field('', max_length=200)


class RunBody(BaseModel):
    difficulty: str = Field(max_length=20)
    won: bool
    score: int = Field(ge=0)
    time_seconds: float = Field(ge=0)
    lives_lost: int = Field(ge=0)
    waves_cleared: int = Field(ge=0)
    kills: int = Field(ge=0)


class RoleBody(BaseModel):
    role: str = Field(max_length=10)


class NotLoggedIn(Exception):
    pass


def _error(status, kind, detail):
    return JSONResponse(status_code=status, content={'error': kind, 'detail': detail})


def _session(backend, account):
    return {'token': backend.issue_token(account), 'account': asdict(account)}


def create_app(backend=None):
    backend = backend or SqlBackend(os.environ.get('DATABASE_URL', DEFAULT_URL))
    app = FastAPI(title='KARZ Tower Defense API')
    app.state.backend = backend

    @app.exception_handler(AccountError)
    async def account_error(request: Request, exc: AccountError):
        return _error(400, 'account', str(exc))

    @app.exception_handler(AccessDenied)
    async def access_denied(request: Request, exc: AccessDenied):
        return _error(403, 'access', str(exc))

    @app.exception_handler(ValueError)
    async def value_error(request: Request, exc: ValueError):
        return _error(400, 'value', str(exc))

    @app.exception_handler(NotLoggedIn)
    async def not_logged_in(request: Request, exc: NotLoggedIn):
        return _error(401, 'auth', 'Your session expired. Please log in again.')

    @app.exception_handler(RequestValidationError)
    async def bad_request(request: Request, exc: RequestValidationError):
        return _error(422, 'request', 'The game sent a request the server could not understand.')

    def bearer(authorization: Optional[str] = Header(None)):
        if not authorization or not authorization.startswith('Bearer '):
            raise NotLoggedIn()
        return authorization[len('Bearer '):]

    def current_account(token: str = Depends(bearer)):
        account = backend.account_for_token(token)
        if account is None:
            raise NotLoggedIn()
        return account

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    @app.post('/auth/signup')
    def sign_up(body: SignUpBody):
        return _session(backend, backend.sign_up(body.name, body.username, body.email, body.password))

    @app.post('/auth/login')
    def log_in(body: LogInBody):
        return _session(backend, backend.log_in(body.email, body.password))

    @app.post('/auth/logout')
    def log_out(token: str = Depends(bearer)):
        backend.revoke_token(token)
        return {'status': 'ok'}

    @app.get('/me')
    def me(account=Depends(current_account)):
        return asdict(account)

    @app.put('/me')
    def update_me(body: UpdateBody, account=Depends(current_account)):
        return asdict(backend.update_account(account, body.current_password, body.name, body.username, body.email,
                                             body.new_password))

    @app.get('/me/unlocked')
    def unlocked(account=Depends(current_account)):
        return {'difficulties': list(backend.unlocked_difficulties(account))}

    @app.post('/me/runs')
    def record_run(body: RunBody, account=Depends(current_account)):
        return {'unlocked': list(backend.record_run(account, RunResult(**body.model_dump())))}

    @app.get('/leaderboard/{kind}')
    def leaderboard(kind: str, difficulty: Optional[str] = None, limit: int = Query(LEADERBOARD_SIZE, ge=1, le=100)):
        return [asdict(entry) for entry in backend.leaderboard(kind, difficulty, limit)]

    @app.get('/admin/accounts')
    def list_accounts(account=Depends(current_account)):
        return [{**asdict(s), 'unlocked': list(s.unlocked)} for s in backend.list_accounts(account)]

    @app.put('/admin/accounts/{account_id}/role')
    def set_role(account_id: int, body: RoleBody, account=Depends(current_account)):
        return asdict(backend.set_role(account, account_id, body.role))

    return app
