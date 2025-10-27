from fastapi import APIRouter, HTTPException, Request
from typing import Dict
import uuid

from src.config.database import get_redis_client

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login(payload: Dict[str, str]):
    """
    Login simplificado: recibe { "userId": "..." } y devuelve sessionId.
    Nota: en una app real debería validarse credenciales y no aceptar solo userId.
    """
    user_id = payload.get("userId")
    if not user_id:
        raise HTTPException(status_code=400, detail="userId is required")

    session_id = uuid.uuid4().hex
    ttl_seconds = 3600  # 1 hora

    try:
        r = get_redis_client()
        # SET con expiración
        r.set(session_id, user_id, ex=ttl_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {e}")

    return {"sessionId": session_id, "expires_in": ttl_seconds}


@router.post("/logout")
def logout(request: Request):
    """
    Elimina la sesión enviada en el header X-Session-Id.
    """
    session_id = request.headers.get("X-Session-Id")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-Id header required")

    try:
        r = get_redis_client()
        deleted = r.delete(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {e}")

    if deleted == 0:
        # key didn't exist
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Logged out"}


@router.post("/refresh")
def refresh_session(request: Request):
    """
    Refresh de sesión: intercambia la sessionId actual por una nueva con TTL de 1 hora.
    - Requiere header X-Session-Id con la sesión vigente.
    - Devuelve { sessionId, expires_in }.
    """
    old_session = request.headers.get("X-Session-Id")
    if not old_session:
        raise HTTPException(status_code=400, detail="X-Session-Id header required")

    ttl_seconds = 3600
    try:
        r = get_redis_client()
        user_id = r.get(old_session)
        if not user_id:
            raise HTTPException(status_code=401, detail="Session invalid or expired")

        # Crear nueva session id
        new_session = uuid.uuid4().hex
        r.set(new_session, user_id, ex=ttl_seconds)
        # Borrar la antigua
        try:
            r.delete(old_session)
        except Exception:
            # No crítico si no se pudo borrar
            pass

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {e}")

    return {"sessionId": new_session, "expires_in": ttl_seconds}
