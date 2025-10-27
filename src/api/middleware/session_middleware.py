from fastapi import Request
from fastapi.responses import JSONResponse
import logging

from src.config.database import get_redis_client


async def session_middleware(request: Request, call_next):
    """
    Middleware HTTP que lee el header `X-Session-Id`, resuelve el userId en Redis
    y lo asigna a `request.state.user_id`.

    Comportamiento:
    - Si no viene `X-Session-Id` deja `request.state.user_id = None` (compatibilidad)
    - Si viene pero Redis no devuelve userId -> responde 401
    - Si hay error de conexión con Redis -> responde 500
    """
    request.state.user_id = None
    session_id = request.headers.get("X-Session-Id")
    if not session_id:
        # No hay sesión, dejamos la request sin user_id (compatibilidad hacia atrás)
        return await call_next(request)

    try:
        r = get_redis_client()
        user_id = r.get(session_id)
    except Exception as e:
        logging.error(f"🔴 Error conectando a Redis desde session_middleware: {e}")
        return JSONResponse(status_code=500, content={"detail": "Redis connection error"})

    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Session invalid or expired"})

    # Guardamos el user id resuelto para que las rutas lo usen
    request.state.user_id = user_id
    return await call_next(request)
