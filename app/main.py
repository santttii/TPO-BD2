import os
from dotenv import load_dotenv
from mongo_service import probar_mongo
from neo4j_service import probar_neo4j
from redis_service import probar_redis

load_dotenv()

print("🔄 Iniciando pruebas de conexión...")

probar_mongo()
probar_neo4j()
probar_redis()

print("✅ Todas las conexiones funcionan correctamente.")
