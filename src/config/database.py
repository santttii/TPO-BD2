import os
from pymongo import MongoClient
import redis
from neo4j import GraphDatabase

# ==================================
# 🟢 MongoDB Connection Test
# ==================================
def probar_mongo():
    """Prueba la conexión a MongoDB usando la URI y la DB del entorno."""
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DATABASE") # <-- Obtener el nombre de la DB
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping') 
        
        # 🚨 CAMBIO AQUÍ: Conectar directamente a la base de datos nombrada
        db = client[db_name] 
        
        print(f"🟢 Mongo conectado a la base: {db.name}")
        return client
    except Exception as e:
        print(f"❌ Error al conectar a MongoDB: {e}")
        return None

# ==================================
# 🕸 Neo4j Connection Test
# ==================================
def probar_neo4j():
    """Prueba la conexión a Neo4j usando el driver Bolt."""
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            # Solo probamos la conexión con una consulta simple
            session.run("RETURN 1")
            print("🕸️ Conectado correctamente a Neo4j.")
        return driver
    except Exception as e:
        print(f"❌ Error al conectar a Neo4j: {e}")
        return None
    finally:
        # Nota: En una aplicación real, el driver se inicializa una vez 
        # y no se cierra hasta el apagado de la app.
        pass # Dejo el cierre fuera para un uso de prueba rápido

# ==================================
# ⚡ Redis Connection Test
# ==================================
def probar_redis():
    """Prueba la conexión a Redis e intenta obtener un valor de prueba."""
    # En tu .env original no incluiste REDIS_URI, pero usaste las vars de Host/Port
    # Asumo que tu app usa REDIS_URI (que era redis://redis:6379/) o las otras variables.
    # Si usas REDIS_URI:
    uri = os.getenv("REDIS_URI")
    try:
        r = redis.from_url(uri)
        # Prueba de conexión con PING
        r.ping() 
        # Si tienes el valor 'saludo' guardado del ejemplo anterior
        valor_guardado = r.get('saludo')
        if valor_guardado:
            print(f"⚡ Redis conectado. Valor guardado (saludo): {valor_guardado.decode()}")
        else:
            print("⚡ Redis conectado. No se encontró el valor de prueba 'saludo'.")
        return r
    except Exception as e:
        print(f"❌ Error al conectar a Redis: {e}")
        return None

# ==================================
# Función de prueba principal
# ==================================
def inicializar_conexiones():
    """Llama a todas las funciones de prueba de conexión."""
    print("\n--- Probando Conexiones a Bases de Datos ---")
    probar_mongo()
    probar_neo4j()
    probar_redis()
    print("--------------------------------------------\n")

if __name__ == "__main__":
    # Esto permite ejecutar el archivo directamente para probar
    inicializar_conexiones()