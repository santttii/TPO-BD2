from fastapi import APIRouter, HTTPException, Request
from typing import Dict
import uuid
from datetime import datetime
import logging
from bson import ObjectId

from src.utils.security import hash_password, verify_password
from src.repositories.user_repository import UserRepository
from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository
from src.config.database import get_redis_client, get_mongo_db
from src.models.user_model import UserIn

router = APIRouter(prefix="/auth", tags=["Auth"])

user_repo = UserRepository()
graph_repo = Neo4jRepository()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@router.post("/register")
def register(payload: UserIn):
    db = get_mongo_db()
    users = db.get_collection("users")
    people = db.get_collection("people")

    logging.info(f"🟦 Intentando registrar usuario: {payload.username}")

    # 🔒 Verificar usuario existente
    if users.find_one({"username": payload.username}):
        logging.warning("⚠️ Usuario ya existe en MongoDB.")
        raise HTTPException(status_code=400, detail="Username already exists")

    try:
        # 👤 Crear usuario
        pwd_hash = hash_password(payload.password)
        user_doc = {
            "username": payload.username,
            "password_hash": pwd_hash,
            "created_at": datetime.utcnow(),
        }

        res = users.insert_one(user_doc)
        logging.info(f"✅ Usuario creado con _id={res.inserted_id}")
        user_id = str(res.inserted_id)

        # 👥 Crear persona vinculada
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

        logging.info("🟨 Intentando insertar en colección 'people'...")
        result_people = people.insert_one(person_doc)
        logging.info(f"✅ Resultado insert_one: acknowledged={result_people.acknowledged}, id={result_people.inserted_id}")

        # 🌐 Crear nodo en Neo4j
        try:
            logging.info("🌍 Intentando crear nodo en Neo4j...")
            graph_repo.create_person_node(
                person_id=user_id,
                nombre=payload.username,
                rol="Usuario"
            )
            logging.info("✅ Nodo creado correctamente en Neo4j.")
        except Exception as neo_err:
            logging.error(f"⚠️ Error creando nodo en Neo4j: {neo_err}")

        return {"id": user_id, "username": payload.username}

    except Exception as e:
        logging.error(f"❌ Error creando usuario o persona: {e}")
        raise HTTPException(status_code=500, detail=f"Error creando usuario o persona: {e}")

@router.post("/login")
def login(payload: Dict[str, str]):
    """
    Login con credenciales: { "username": "..", "password": ".." }
    Devuelve token con sessionId en Redis.
    """
    username = payload.get("username")
    password = payload.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    user = user_repo.find_by_username(username)
    if not user or not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(user["_id"])
    session_id = uuid.uuid4().hex
    ttl_seconds = 3600

    try:
        r = get_redis_client()
        r.set(session_id, user_id, ex=ttl_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {e}")

    return {
        "sessionId": session_id,
        "token": session_id,
        "auth_header": f"Bearer {session_id}",
        "expires_in": ttl_seconds,
    }
