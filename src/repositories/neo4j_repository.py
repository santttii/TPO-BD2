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
    # 👤 Crear nodo Person y vincular habilidades
    # ===============================================================
    def create_person_node(self, person_id: str, nombre: str, rol: str):
        """
        Crea (si no existe) el nodo de Persona en Neo4j.
        """
        with self.driver.session() as session:
            session.run(
                """
                MERGE (p:Person {id: $pid})
                SET p.nombre = $nombre,
                    p.rol = $rol
                """,
                pid=person_id,
                nombre=nombre,
                rol=rol
            )

    def link_person_to_skill(self, person_id: str, skill_name: str):
        """
        Crea (si no existe) la relación (:Person)-[:POSEE_HABILIDAD]->(:Skill)
        """
        with self.driver.session() as session:
            session.run(
                """
                MERGE (p:Person {id: $pid})
                MERGE (s:Skill {nombre: $skill})
                MERGE (p)-[:POSEE_HABILIDAD]->(s)
                """,
                pid=person_id,
                skill=skill_name
            )


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

    def get_common_connections(self, person_id: str, other_id: str):
        """
        Devuelve las personas que están conectadas tanto con `person_id` como con `other_id`.
        Ejemplo: (A)-[]->(C)<-[]-(B)
        """
        query = """
        MATCH (a:Person {id: $id1})-[]->(common:Person)<-[]-(b:Person {id: $id2})
        RETURN DISTINCT common.id AS id, common.nombre AS nombre, common.rol AS rol
        """
        with self.driver.session() as session:
            result = session.run(query, id1=person_id, id2=other_id)
            return [dict(r) for r in result]
    def get_suggested_connections(self, person_id: str):
        """
        Devuelve personas sugeridas que no están conectadas directamente,
        pero comparten al menos una conexión en común.
        """
        query = """
        MATCH (p:Person {id: $id})-[]->(amigo:Person)-[]->(sugerido:Person)
        WHERE NOT (p)-[]-(sugerido) AND p <> sugerido
        RETURN DISTINCT sugerido.id AS id, sugerido.nombre AS nombre, sugerido.rol AS rol
        LIMIT 5
        """
        with self.driver.session() as session:
            result = session.run(query, id=person_id)
            return [dict(r) for r in result]
    def delete_connection(self, source_id: str, target_id: str, tipo: str = None):
        """
        Elimina una conexión (o todas) entre dos personas.
        Si se pasa un tipo, borra solo esa relación.
        Ejemplo:
          - delete_connection(A, B) -> borra todas las relaciones A↔B
          - delete_connection(A, B, "MENTORSHIP") -> borra solo las de ese tipo
        """
        try:
            if tipo:
                rel_type = tipo.upper().replace(" ", "_")
                query = f"""
                MATCH (a:Person {{id: $src}})-[r:{rel_type}]-(b:Person {{id: $tgt}})
                DELETE r
                RETURN COUNT(r) AS eliminadas
                """
            else:
                query = """
                MATCH (a:Person {id: $src})-[r]-(b:Person {id: $tgt})
                DELETE r
                RETURN COUNT(r) AS eliminadas
                """

            with self.driver.session() as session:
                result = session.run(query, src=source_id, tgt=target_id)
                data = result.single()
                count = data["eliminadas"] if data else 0

                logging.info(f"🗑️ Eliminadas {count} relaciones entre {source_id} y {target_id}")
                return count

        except Exception as e:
            logging.error(f"❌ Error eliminando conexión: {e}")
            raise
    # ===============================================================
    # 🏢 CREAR NODO COMPANY
    # ===============================================================
    def create_company_node(self, company_id: str, nombre: str, industria: str):
        """
        Crea (o actualiza) un nodo Company en Neo4j.
        """
        with self.driver.session() as session:
            session.run(
                """
                MERGE (c:Company {id: $id})
                SET c.nombre = $nombre, c.industria = $industria
                """,
                id=company_id,
                nombre=nombre,
                industria=industria,
            )
        logging.info(f"🏢 Nodo Company creado o actualizado: {nombre} ({industria})")

    # ===============================================================
    # 🤝 RELACIÓN PERSONA ↔ COMPANY
    # ===============================================================
    def link_person_to_company(self, person_id: str, company_id: str, role: str = "TRABAJA_EN"):
        """
        Crea una relación (Person)-[:TRABAJA_EN]->(Company).
        """
        rel_type = role.upper().replace(" ", "_")
        logging.info(f"🧩 Vinculando persona {person_id} con empresa {company_id} ({rel_type})")

        query = f"""
        MATCH (p:Person {{id: $pid}}), (c:Company {{id: $cid}})
        MERGE (p)-[r:{rel_type}]->(c)
        RETURN COUNT(r) AS total
        """

        with self.driver.session() as session:
            res = session.run(query, pid=person_id, cid=company_id)
            total = res.single()["total"]
            logging.info(f"✅ Relación {rel_type} creada. Total relaciones: {total}")

    # ===============================================================
    # 🧩 RELACIÓN ENTRE EMPRESAS
    # ===============================================================
    def link_company_to_company(self, company_a: str, company_b: str, tipo: str = "PARTNER_DE"):
        """
        Crea una relación entre empresas (CompanyA)-[:PARTNER_DE]->(CompanyB)
        """
        rel_type = tipo.upper().replace(" ", "_")
        logging.info(f"🏗️ Vinculando empresas {company_a} -[{rel_type}]-> {company_b}")

        query = f"""
        MATCH (a:Company {{id: $a}}), (b:Company {{id: $b}})
        MERGE (a)-[r:{rel_type}]->(b)
        RETURN COUNT(r) AS total
        """

        with self.driver.session() as session:
            res = session.run(query, a=company_a, b=company_b)
            total = res.single()["total"]
            logging.info(f"✅ Relación {rel_type} creada entre empresas. Total: {total}")
            
    def delete_node_by_id(self, node_id: str, label: str = "Company"):
        with self.driver.session() as session:
            session.run(f"MATCH (n:{label} {{id: $id}}) DETACH DELETE n", id=node_id)
            logging.info(f"🗑️ Nodo {label} eliminado: {node_id}")

    # ===============================================================
    # 💼 CREAR NODO JOB
    # ===============================================================
    def create_job_node(self, job_id: str, titulo: str, empresa_id: str):
        """
        Crea un nodo Job y lo conecta con la empresa que lo publica.
        """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (e:Company {id: $empresa_id})
                CREATE (j:Job {id: $id, titulo: $titulo})
                MERGE (e)-[:PUBLICA]->(j)
                """,
                id=job_id,
                titulo=titulo,
                empresa_id=empresa_id
            )

    # ===============================================================
    # 🧍 PERSONA POSTULA A JOB
    # ===============================================================
    def apply_to_job(self, person_id: str, job_id: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Person {id: $pid}), (j:Job {id: $jid})
                MERGE (p)-[:POSTULA_A]->(j)
                """,
                pid=person_id,
                jid=job_id
            )

    def get_applicants_for_job(self, job_id: str):
        """
        Devuelve todas las personas que postularon a un Job.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Person)-[:POSTULA_A]->(j:Job {id: $jid})
                RETURN p.id AS personId, p.nombre AS nombre, p.rol AS rol
                """,
                jid=job_id
            )
            return [dict(r) for r in result]

    # ===============================================================
    # 🧭 OBTENER EMPLEOS A LOS QUE UNA PERSONA SE POSTULÓ
    # ===============================================================
    def get_jobs_for_person(self, person_id: str):
        """
        Devuelve todos los empleos a los que una persona se postuló.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Person {id: $pid})-[:POSTULA_A]->(j:Job)
                OPTIONAL MATCH (e:Company)-[:PUBLICA]->(j)
                RETURN 
                    j.id AS jobId,
                    j.titulo AS titulo,
                    j.descripcion AS descripcion,
                    e.id AS empresaId,
                    e.nombre AS empresaNombre
                """,
                pid=person_id
            )
            return [dict(r) for r in result]

    def get_applications(self, person_id: str):
        """
        Devuelve todos los empleos a los que una persona se postuló.
        """
        try:
            return self.graph_repo.get_jobs_for_person(person_id)
        except Exception as e:
            raise Exception(f"Error obteniendo empleos postulados: {e}")

    # ===============================================================
    # 🧩 VINCULAR JOB A SKILLS (obligatorias o deseables)
    # ===============================================================
    def link_job_to_skill(self, job_id: str, skill_name: str, tipo: str):
        """
        Crea o vincula una habilidad al Job según tipo de requisito.
        tipo puede ser: 'REQUERIMIENTO_DE' o 'DESEA'
        """
        with self.driver.session() as session:
            session.run(
                f"""
                MATCH (j:Job {{id: $job_id}})
                MERGE (s:Skill {{nombre: $skill}})
                MERGE (j)-[r:{tipo}]->(s)
                """,
                job_id=job_id,
                skill=skill_name
            )
