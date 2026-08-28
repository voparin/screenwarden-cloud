from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from cloud.api.limiter import limiter
from cloud.api.routes import auth, devices, users, sync


def create_app() -> FastAPI:
    app = FastAPI(title="screenwarden-cloud")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(devices.router, prefix="/devices", tags=["devices"])
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(sync.router, tags=["sync"])

    return app


app = create_app()
