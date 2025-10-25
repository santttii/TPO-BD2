import os
from pymongo import MongoClient
import redis
from neo4j import GraphDatabase

# ==============================================================
# 🟢 MongoDB
# ==============================================================
def get_mongo_db():
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DATABASE", "tpo_database")

    client = MongoClient(uri)
    db = client[db_name]  # ✅ devolvemos la base, no el cliente
    return db

def probar_mongo():
    """Prueba de conexión a MongoDB"""
    try:
        db = get_mongo_db()
        db.command("ping")
        print(f"🟢 Conectado a MongoDB → Base: {db.name}")
        return db
    except Exception as e:
        print(f"❌ Error al conectar a MongoDB: {e}")
        return None


# ==============================================================
# 🕸️ Neo4j
# ==============================================================

def get_neo4j_driver():
    """
    Devuelve el driver de Neo4j.
    URI de ejemplo (Docker): bolt://neo4j:7687
    """
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))


def probar_neo4j():
    """Prueba la conexión a Neo4j"""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            session.run("RETURN 1")
        print("🕸️ Conectado correctamente a Neo4j.")
        return driver
    except Exception as e:
        print(f"❌ Error al conectar a Neo4j: {e}")
        return None


# ==============================================================
# ⚡ Redis
# ==============================================================

def get_redis_client():
    """
    Devuelve el cliente Redis.
    URI típica en Docker: redis://redis:6379/
    """
    uri = os.getenv("REDIS_URI", "redis://redis:6379/")
    return redis.from_url(uri, decode_responses=True)


def probar_redis():
    """Prueba de conexión a Redis"""
    try:
        r = get_redis_client()
        r.ping()
        valor = r.get("saludo")
        if valor:
            print(f"⚡ Redis conectado. Valor guardado (saludo): {valor}")
        else:
            print("⚡ Redis conectado correctamente.")
        return r
    except Exception as e:
        print(f"❌ Error al conectar a Redis: {e}")
        return None


# ==============================================================
# 🚀 Inicialización General
# ==============================================================

def inicializar_conexiones():
    """Llama a todas las funciones de prueba de conexión."""
    print("\n--- Probando Conexiones a Bases de Datos ---")
    probar_mongo()
    probar_neo4j()
    probar_redis()
    print("--------------------------------------------\n")
