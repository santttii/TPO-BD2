import logging
from src.config.database import get_neo4j_driver

# Configuración global de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class Neo4jRepository:
    """
    Repositorio para manejar nodos y relaciones en Neo4j.
    """

    def __init__(self):
        self.driver = get_neo4j_driver()

    # ===============================================================
    # 👤 CREAR NODO PERSONA
    # ===============================================================
    def create_person_node(self, person_id: str, name: str, role: str):
        with self.driver.session() as session:
            session.run(
                """
                MERGE (p:Person {id: $id})
                SET p.nombre = $name, p.rol = $role
                """,
                id=person_id,
                name=name,
                role=role
            )
            logging.info(f"🧍 Nodo Person creado o actualizado: {name} ({role})")

    # ===============================================================
    # 🔗 CONEXIÓN UNIDIRECCIONAL
    # ===============================================================
    def create_connection_one_way(self, source_id: str, target_id: str, tipo: str = "SIGUE_A"):
        """
        Crea una relación unidireccional del tipo especificado.
        Ejemplo: (A)-[:SIGUE_A]->(B)
        """
        rel_type = tipo.upper().replace(" ", "_")  # ej: "mentorship" -> "MENTORSHIP"
        logging.info(f"➡️ Creando conexión unidireccional: {source_id} -[{rel_type}]-> {target_id}")

        query = f"""
        MATCH (a:Person {{id: $src}}), (b:Person {{id: $tgt}})
        MERGE (a)-[r:{rel_type}]->(b)
        RETURN COUNT(r) AS total
        """

        with self.driver.session() as session:
            result = session.run(query, src=source_id, tgt=target_id)
            data = result.single()
            count = data["total"] if data else 0
            logging.info(f"✅ Conexión {rel_type} creada. Total relaciones: {count}")

    # ===============================================================
    # 🔁 CONEXIÓN BIDIRECCIONAL
    # ===============================================================
    def create_connection_two_way(self, source_id: str, target_id: str, tipo: str = "COLABORA_CON"):
        """
        Crea relaciones bidireccionales entre dos personas.
        Ejemplo: (A)-[:COLABORA_CON]->(B) y (B)-[:COLABORA_CON]->(A)
        """
        rel_type = tipo.upper().replace(" ", "_")
        logging.info(f"🔁 Creando conexión bidireccional: {source_id} <-> {target_id} ({rel_type})")

        query = f"""
        MATCH (a:Person {{id: $src}}), (b:Person {{id: $tgt}})
        MERGE (a)-[r:{rel_type}]->(b)
        MERGE (b)-[r2:{rel_type}]->(a)
        RETURN COUNT(r) AS total
        """

        with self.driver.session() as session:
            result = session.run(query, src=source_id, tgt=target_id)
            data = result.single()
            count = data["total"] if data else 0
            logging.info(f"✅ Conexión bidireccional {rel_type} creada. Total relaciones: {count}")

    # ===============================================================
    # 🌐 OBTENER RED DE CONEXIONES (con tipo)
    # ===============================================================
    def get_network(self, person_id: str):
        """
        Devuelve las conexiones salientes con su tipo.
        Ejemplo de salida:
        [
          {"targetId": "2", "nombre": "Jochi", "rol": "Developer", "tipo": "MENTORSHIP"},
          {"targetId": "3", "nombre": "Lucas", "rol": "Analyst", "tipo": "COLABORA_CON"}
        ]
        """
        query = """
        MATCH (p:Person {id: $id})-[r]->(otro:Person)
        RETURN otro.id AS targetId, otro.nombre AS nombre, otro.rol AS rol, type(r) AS tipo
        """
        with self.driver.session() as session:
            result = session.run(query, id=person_id)
            data = [dict(r) for r in result]
            logging.info(f"🌐 {len(data)} conexiones encontradas para {person_id}")
            return data

    # ===============================================================
    # 💡 OBTENER RECOMENDACIONES (ejemplo futuro)
    # ===============================================================
    def get_recommendations(self, person_id: str):
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Person {id: $id})-[:POSEE_HABILIDAD]->(h:Habilidad)<-[:REQUERIMIENTO_DE]-(e:Empleo)
                RETURN e.id AS empleoId, e.titulo AS titulo, COUNT(h) AS afinidad
                ORDER BY afinidad DESC
                LIMIT 5
                """,
                id=person_id
            )
            return [dict(r) for r in result]
