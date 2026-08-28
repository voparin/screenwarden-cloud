from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def _device_or_ip(request: Request) -> str:
    return request.headers.get("x-device-token") or get_remote_address(request)


limiter = Limiter(key_func=get_remote_address)
sync_limiter = Limiter(key_func=_device_or_ip)
