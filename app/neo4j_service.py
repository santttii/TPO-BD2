from neo4j import GraphDatabase
import os

def probar_neo4j():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            # Solo probamos la conexión con una consulta simple
            session.run("RETURN 1")
            print("🕸️ Conectado correctamente a Neo4j.")
    finally:
        driver.close()
