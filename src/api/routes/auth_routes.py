from fastapi import APIRouter, HTTPException, Request
from typing import Dict
import uuid

from src.config.database import get_redis_client, get_mongo_db
from src.utils.security import hash_password, verify_password
from src.models.user_model import UserIn, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register(payload: UserIn):
    """Registro mínimo: username + password. Guarda hash en MongoDB."""
    db = get_mongo_db()
    users = db.get_collection("users")

    # Verificar existencia
    if users.find_one({"username": payload.username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    try:
        pwd_hash = hash_password(payload.password)
        doc = {"username": payload.username, "password_hash": pwd_hash}
        res = users.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mongo error: {e}")

    return {"id": str(res.inserted_id), "username": payload.username}


@router.post("/login")
def login(payload: Dict[str, str]):
    """
    Login con credenciales: { "username": "..", "password": ".." }
    Devuelve sessionId/token como antes si las credenciales son correctas.
    """
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    # Buscar usuario
    db = get_mongo_db()
    users = db.get_collection("users")
    user = users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(user.get("_id"))

    session_id = uuid.uuid4().hex
    ttl_seconds = 3600  # 1 hora

    try:
        r = get_redis_client()
        # SET con expiración
        r.set(session_id, user_id, ex=ttl_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {e}")

    # Devolvemos token listo para Authorization
    return {
        "sessionId": session_id,
        "token": session_id,
        "auth_header": f"Bearer {session_id}",
        "expires_in": ttl_seconds,
    }


@router.post("/logout")
def logout(request: Request):
    """
    Elimina la sesión enviada en el header X-Session-Id.
    """
    # Aceptar Authorization: Bearer <token> o X-Session-Id
    auth_header = request.headers.get("authorization")
    session_id = None
    if auth_header and isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
        session_id = auth_header.split(" ", 1)[1].strip()
    else:
        session_id = request.headers.get("x-session-id")

    if not session_id:
        raise HTTPException(status_code=400, detail="Authorization Bearer token or X-Session-Id header required")

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
    # Soportar Authorization: Bearer <token> o X-Session-Id
    auth_header = request.headers.get("authorization")
    old_session = None
    if auth_header and isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
        old_session = auth_header.split(" ", 1)[1].strip()
    else:
        old_session = request.headers.get("x-session-id")

    if not old_session:
        raise HTTPException(status_code=400, detail="Authorization Bearer token or X-Session-Id header required")

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
