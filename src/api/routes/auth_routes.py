from fastapi import APIRouter, HTTPException, Request
from typing import Dict
import uuid
from datetime import datetime

from src.utils.security import hash_password, verify_password
from src.config.database import get_mongo_db, get_redis_client
from src.models.user_model import UserIn
from src.repositories.neo4j_repository import Neo4jRepository

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register(payload: UserIn):
    db = get_mongo_db()
    users = db.get_collection("users")
    people = db.get_collection("people")

    if users.find_one({"username": payload.username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    pwd_hash = hash_password(payload.password)
    user_doc = {
        "username": payload.username,
        "password_hash": pwd_hash,
        "created_at": datetime.utcnow()
    }
    res = users.insert_one(user_doc)
    user_id = str(res.inserted_id)

    # create minimal person profile
    person_doc = {
        "userId": user_id,
        "correo": f"{payload.username}@talentum.local",
        "rol": "Usuario",
        "datosPersonales": {"nombre": payload.username},
        "perfil": {"bio": "", "disponible": True},
        "experiencia": [],
        "educacion": [],
        "intereses": [],
        "conexiones": [],
        "empresaActualId": None,
        "creadoEn": datetime.utcnow(),
        "actualizadoEn": datetime.utcnow(),
    }
    people.insert_one(person_doc)

    # Crear nodo en Neo4j para la persona recién creada (si Neo4j está disponible)
    try:
        neo = Neo4jRepository()
        nombre = person_doc.get("datosPersonales", {}).get("nombre", payload.username)
        rol = person_doc.get("rol", "Usuario")
        neo.create_person_node(person_id=user_id, nombre=nombre, rol=rol)
    except Exception:
        # No queremos que la falla de Neo4j rompa el registro; solo logueamos y seguimos
        pass

    return {"id": user_id, "username": payload.username}


@router.post("/login")
def login(payload: UserIn):
    """Login con username + password en el body. Crea sesión en Redis y devuelve token + datos básicos de sesión."""
    username = payload.username
    password = payload.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    db = get_mongo_db()
    users = db.get_collection("users")
    people = db.get_collection("people")

    user = users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored = user.get("password_hash", "")
    if not verify_password(password, stored):
        # fall back: more descriptive reason, but don't leak which part failed
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(user.get("_id"))
    session_id = uuid.uuid4().hex
    ttl_seconds = 3600

    try:
        r = get_redis_client()
        r.set(session_id, user_id, ex=ttl_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {e}")

    # obtener persona asociada si existe
    person = people.find_one({"userId": user_id})
    person_id = str(person.get("_id")) if person else None

    return {
        "sessionId": session_id,
        "token": session_id,
        "auth_header": f"Bearer {session_id}",
        "expires_in": ttl_seconds,
        "user": {"id": user_id, "username": user.get("username")},
        "personId": person_id,
    }


@router.post("/logout")
def logout(request: Request):
    auth = request.headers.get("authorization")
    sid = None
    if auth and auth.lower().startswith("bearer "):
        sid = auth.split(" ", 1)[1].strip()
    else:
        sid = request.headers.get("x-session-id")

    if not sid:
        raise HTTPException(status_code=400, detail="No session provided")

    try:
        r = get_redis_client()
        r.delete(sid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {e}")

    return {"message": "Logged out"}


@router.post("/refresh")
def refresh(request: Request):
    auth = request.headers.get("authorization")
    sid = None
    if auth and auth.lower().startswith("bearer "):
        sid = auth.split(" ", 1)[1].strip()
    else:
        sid = request.headers.get("x-session-id")

    if not sid:
        raise HTTPException(status_code=400, detail="No session provided")

    try:
        r = get_redis_client()
        user_id = r.get(sid)
        if not user_id:
            raise HTTPException(status_code=401, detail="Session invalid or expired")
        # rotate
        new_sid = uuid.uuid4().hex
        ttl_seconds = 3600
        r.set(new_sid, user_id, ex=ttl_seconds)
        r.delete(sid)
        return {"sessionId": new_sid, "token": new_sid, "expires_in": ttl_seconds}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {e}")
