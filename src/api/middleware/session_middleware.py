from fastapi import Request
from fastapi.responses import JSONResponse
import logging
from src.config.database import get_redis_client


async def session_middleware(request: Request, call_next):
    """
    Middleware HTTP que valida la sesión antes de procesar la request.
    - Excluye rutas públicas (/auth, /docs, /openapi, /)
    - Requiere token válido (Authorization: Bearer o X-Session-Id) para las demás
    - Si el token no existe o expiró, responde 401
    """

    path = request.url.path
    request.state.user_id = None

    # ✅ Excepciones: rutas públicas
    if (
        path.startswith("/api/v1/auth")
        or path in ["/", "/docs", "/openapi.json"]
        or path.startswith("/favicon")
    ):
        return await call_next(request)

    # 🔐 Obtener token (Bearer o X-Session-Id)
    auth_header = request.headers.get("authorization")
    session_id = None

    if auth_header and isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
        session_id = auth_header.split(" ", 1)[1].strip()
    else:
        session_id = request.headers.get("x-session-id")

    # 🚫 Si no hay token → bloquear acceso
    if not session_id:
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid session token"})

    try:
        r = get_redis_client()
        user_id = r.get(session_id)
    except Exception as e:
        logging.error(f"🔴 Error conectando a Redis desde session_middleware: {e}")
        return JSONResponse(status_code=500, content={"detail": "Redis connection error"})

    # 🚫 Si no existe en Redis → sesión expirada o inválida
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Session invalid or expired"})

    # ✅ Decodificar user_id si es necesario
    if isinstance(user_id, bytes):
        try:
            user_id = user_id.decode("utf-8")
        except Exception:
            pass

    request.state.user_id = user_id

    # ✅ Pasar la request al siguiente handler
    return await call_next(request)
