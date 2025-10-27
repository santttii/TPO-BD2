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

    def link_person_to_skill(self, person_id: str, skill_name: str, nivel: int = 1):
        """
        Crea un nodo Skill si no existe y vincula la persona con un nivel.
        Ejemplo: (p)-[:POSEE_HABILIDAD {nivel: 4}]->(s)
        """
        with self.driver.session() as session:
            session.run(
                """
                MERGE (s:Skill {nombre: $skill})
                WITH s
                MATCH (p:Person {id: $pid})
                MERGE (p)-[r:POSEE_HABILIDAD]->(s)
                SET r.nivel = $nivel
                """,
                pid=person_id,
                skill=skill_name,
                nivel=nivel
            )
            print(f"🔗 Vinculada habilidad '{skill_name}' (nivel {nivel}) con persona {person_id}")


    def delete_person_skills(self, person_id: str):
        """
        Elimina todas las relaciones POSEE_HABILIDAD de una persona.
        """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Person {id: $pid})-[r:POSEE_HABILIDAD]->(s)
                DELETE r
                """,
                pid=person_id
            )
            logging.info(f"🧹 Eliminadas relaciones POSEE_HABILIDAD para persona {person_id}")



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


    def get_job_recommendations(self, person_id: str, limit: int = 10):
        """
        Devuelve empleos compatibles con una persona según sus habilidades y nivel.
        Soporta relaciones:
          - (:Job)-[:REQUERIMIENTO_DE]->(:Skill)
          - (:Job)-[:DESEA]->(:Skill)
          - (:Person)-[:POSEE_HABILIDAD]->(:Skill)
        Además devuelve las habilidades coincidentes.
        """
        query = """
        // 1️⃣ Buscar relaciones entre la persona y los skills que los jobs requieren o desean
        MATCH (p:Person {id: $pid})-[r:POSEE_HABILIDAD]->(s:Skill)
        OPTIONAL MATCH (s)<-[rel1:REQUERIMIENTO_DE]-(job:Job)
        OPTIONAL MATCH (s)<-[rel2:DESEA]-(job)
        
        // 2️⃣ Calcular los puntajes parciales
        WITH p, job, s,
             COALESCE(r.nivel, 1) AS nivelPersona,
             CASE WHEN rel1 IS NOT NULL THEN 2.0 ELSE 0 END AS pesoReq,
             CASE WHEN rel2 IS NOT NULL THEN 1.0 ELSE 0 END AS pesoDesea
             
        // 3️⃣ Calcular score total por job
        WITH job, COLLECT(s.nombre) AS habilidadesCoincidentes,
             SUM(nivelPersona * (pesoReq + pesoDesea)) AS afinidad
        WHERE job IS NOT NULL AND afinidad > 0
        
        RETURN job.id AS jobId,
               job.titulo AS titulo,
               job.descripcion AS descripcion,
               habilidadesCoincidentes,
               ROUND(afinidad, 2) AS score
        ORDER BY score DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            result = session.run(query, pid=person_id, limit=limit)
            return [record.data() for record in result]
    
    def get_person_skills(self, person_id: str):
        """
        Devuelve todas las habilidades de una persona con su nivel.
        Ejemplo:
        [
          {"nombre": "Python", "nivel": 5},
          {"nombre": "Pytorch", "nivel": 4}
        ]
        """
        query = """
        MATCH (p:Person {id: $pid})-[r:POSEE_HABILIDAD]->(s:Skill)
        RETURN s.nombre AS nombre, r.nivel AS nivel
        ORDER BY r.nivel DESC
        """
        with self.driver.session() as session:
            result = session.run(query, pid=person_id)
            return [dict(r) for r in result]

    def get_people_by_skill(self, skill_name: str, min_level: int = 1):
        """
        Devuelve todas las personas que poseen una habilidad (≥ nivel indicado).
        Ejemplo:
        [
          {"personId": "68fab69cb39d7b7931f7ab12", "nombre": "Carla Gómez", "rol": "Data Scientist", "nivel": 5},
          {"personId": "68fab69cb39d7b7931f7ab13", "nombre": "Rodrigo Alcaraz", "rol": "Backend Dev", "nivel": 3}
        ]
        """
        query = """
        MATCH (p:Person)-[r:POSEE_HABILIDAD]->(s:Skill {nombre: $skill})
        WHERE r.nivel >= $min_level
        RETURN p.id AS personId, p.nombre AS nombre, p.rol AS rol, r.nivel AS nivel
        ORDER BY r.nivel DESC
        """
        with self.driver.session() as session:
            result = session.run(query, skill=skill_name, min_level=min_level)
            return [dict(r) for r in result]

    # ===============================================================
    # 📚 MÉTODOS DE CURSOS (sin lambda, sin execute_write)
    # ===============================================================

    def create_course_node(self, course_id: str, titulo: str, proveedor: str | None = None):
        q = """
        MERGE (c:Course {id:$id})
        SET c.titulo=$titulo, c.proveedor=$proveedor
        """
        with self.driver.session() as session:
            session.run(q, id=course_id, titulo=titulo, proveedor=proveedor).consume()

    def link_course_to_skill(self, course_id: str, skill_name: str, nivelMin: int | None = None):
        q = """
        MATCH (c:Course {id:$cid})
        MERGE (s:Skill {nombre:$sname})
        MERGE (c)-[r:REQUIERE]->(s)
        SET r.nivelMin=$nivelMin
        """
        with self.driver.session() as session:
            session.run(q, cid=course_id, sname=skill_name, nivelMin=nivelMin).consume()

    def delete_course_skill_links(self, course_id: str):
        q = "MATCH (:Course {id:$cid})-[r:REQUIERE]->(:Skill) DELETE r"
        with self.driver.session() as session:
            session.run(q, cid=course_id).consume()
        logging.info(f"🔗 Relaciones REQUIERE eliminadas para course {course_id}")

    def link_person_to_course(self, person_id: str, course_id: str):
        q = """
        MATCH (p:Person {id:$pid}), (c:Course {id:$cid})
        MERGE (p)-[:INSCRIPTO_EN]->(c)
        """
        with self.driver.session() as session:
            session.run(q, pid=person_id, cid=course_id).consume()

    def delete_course_node(self, course_id: str):
        q = "MATCH (c:Course {id:$id}) DETACH DELETE c"
        with self.driver.session() as session:
            session.run(q, id=course_id).consume()
        logging.info(f"🗑️ Nodo Course eliminado: {course_id}")

    # --- RELACIÓN DE INSCRIPCIÓN CON PROPIEDADES ---

    # -- Crear/actualizar relación con props (una sola relación) --
    def upsert_inscripcion(self, person_id: str, course_id: str,
                        progreso: int = 0, estado: str = "No empezó",
                        nota: int | None = None, certificacionUrl: str | None = None):
        q = """
        MATCH (p:Person {id:$pid}), (c:Course {id:$cid})
        MERGE (p)-[r:INSCRIPTO_EN]->(c)
        SET r.progreso   = coalesce($progreso, r.progreso, 0),
            r.estado     = coalesce($estado,   r.estado,   'No empezó'),
            r.updatedAt  = datetime()
        FOREACH (_ IN CASE WHEN $nota IS NULL THEN [] ELSE [1] END | SET r.nota = $nota)
        FOREACH (_ IN CASE WHEN $certUrl IS NULL THEN [] ELSE [1] END | SET r.certificacionUrl = $certUrl)
        """
        with self.driver.session() as session:
            session.run(q, pid=str(person_id), cid=str(course_id),
                        progreso=int(progreso), estado=str(estado),
                        nota=nota, certUrl=certificacionUrl).consume()

    def set_inscripcion_progreso(self, person_id: str, course_id: str, progreso: int):
        q = """
        MATCH (p:Person {id:$pid})-[r:INSCRIPTO_EN]->(c:Course {id:$cid})
        SET r.progreso  = $progreso,
            r.estado    = CASE
                            WHEN $progreso >= 100 THEN 'Completado'
                            WHEN $progreso > 0 THEN 'Cursando'
                            ELSE 'No empezó'
                        END,
            r.updatedAt = datetime()
        """
        with self.driver.session() as session:
            session.run(q, pid=str(person_id), cid=str(course_id), progreso=int(progreso)).consume()

    def set_inscripcion_completa(self, person_id: str, course_id: str,
                                nota: int | None = None, certificacionUrl: str | None = None):
        q = """
        MATCH (p:Person {id:$pid})-[r:INSCRIPTO_EN]->(c:Course {id:$cid})
        SET r.estado     = 'Completado',
            r.progreso   = 100,
            r.updatedAt  = datetime()
        FOREACH (_ IN CASE WHEN $nota IS NULL THEN [] ELSE [1] END | SET r.nota = $nota)
        FOREACH (_ IN CASE WHEN $certUrl IS NULL THEN [] ELSE [1] END | SET r.certificacionUrl = $certUrl)
        """
        with self.driver.session() as session:
            session.run(q, pid=str(person_id), cid=str(course_id),
                        nota=nota, certUrl=certificacionUrl).consume()
