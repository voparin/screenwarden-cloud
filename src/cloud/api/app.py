from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from cloud.db.session import create_tables
from cloud.api.routes import auth, devices, users, sync

limiter = Limiter(key_func=get_remote_address)


def create_app() -> FastAPI:
    app = FastAPI(title="screenwarden-cloud")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.on_event("startup")
    def startup():
        create_tables()

    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(devices.router, prefix="/devices", tags=["devices"])
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(sync.router, tags=["sync"])

    return app


app = create_app()
