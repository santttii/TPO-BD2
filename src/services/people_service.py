from typing import Dict, Any, List, Optional
from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository
from src.config.database import get_mongo_db
from datetime import datetime
from src.utils.redis_stats import record_connection


class PeopleService:
    def __init__(self):
        self.repo = MongoRepository("people")
        self.graph_repo = Neo4jRepository()

    # ==============================================
    # 👤 CRUD
    # ==============================================
    
    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea una persona en MongoDB y refleja su nodo + habilidades en Neo4j.
        Soporta:
          - "habilidades": ["Python", "Cassandra"]
          - "perfil.skills": [{"nombre": "python", "nivel": 5}, ...]
        """
        person = self.repo.create(payload)

        # Prefer using provided userId (set by middleware/route) as the canonical person id
        # This keeps compatibility with auth register flow where Neo4j node id == user_id
        provided_user_id = payload.get("userId")
        if provided_user_id:
            person_id = str(provided_user_id)
        else:
            person_id = str(person["_id"])

        # 🧠 Extraer habilidades en ambos formatos
        habilidades = []

        if "habilidades" in payload:
            # Formato simple: ["Python", "Cassandra"]
            habilidades = payload.get("habilidades", [])
        elif "perfil" in payload and "skills" in payload["perfil"]:
            # Formato con nivel: [{"nombre": "python", "nivel": 5}, ...]
            habilidades = payload["perfil"]["skills"]

        try:
            # 1️⃣ Crear nodo Persona
            nombre = payload.get("datosPersonales", {}).get("nombre", "Desconocido")
            rol = payload.get("rol", "Sin Rol")

            self.graph_repo.create_person_node(
                person_id=person_id,
                nombre=nombre,
                rol=rol
            )

            # 2️⃣ Vincular habilidades en Neo4j
            if habilidades:
                print(f"🧠 Vinculando habilidades: {habilidades}")
                for skill in habilidades:
                    if isinstance(skill, str):
                        # Si la lista es simple ["Python", "Cassandra"]
                        self.graph_repo.link_person_to_skill(
                            person_id=person_id,
                            skill_name=skill,
                            nivel=1
                        )
                    elif isinstance(skill, dict):
                        # Si viene como {"nombre": "python", "nivel": 5}
                        nombre_skill = skill.get("nombre")
                        nivel = skill.get("nivel", 1)
                        if nombre_skill:
                            self.graph_repo.link_person_to_skill(
                                person_id=person_id,
                                skill_name=nombre_skill,
                                nivel=nivel
                            )

        except Exception as e:
            print(f"⚠️ Error sincronizando persona y habilidades en Neo4j: {e}")

        person["habilidades"] = habilidades

        # Registrar en historial
        try:
            db = get_mongo_db()
            history = db.get_collection("people_history")
            entry = {
                "person_id": str(person.get("_id") or payload.get("userId")),
                "operation": "create",
                "actor": payload.get("userId"),
                "timestamp": datetime.utcnow(),
                "before": None,
                "after": person
            }
            history.insert_one(entry)
        except Exception:
            pass

        return person



    def list(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Si se busca por userId, intentamos ser tolerantes con el tipo
        # (algunos registros pueden guardar userId como cadena o como ObjectId).
        if filters and "userId" in filters:
            uid = filters.get("userId")
            # 1) intento exacto por string
            try:
                results = self.repo.find({"userId": uid})
                if results:
                    return results
            except Exception:
                pass

            # 2) intentar como ObjectId si tiene formato hex
            try:
                from bson import ObjectId
                oid = ObjectId(uid)
                try:
                    results = self.repo.find({"userId": oid})
                    if results:
                        return results
                except Exception:
                    pass
            except Exception:
                # no es un ObjectId válido -> ignorar
                pass

        return self.repo.find(filters)

    def get(self, person_id: str) -> Optional[Dict[str, Any]]:
        # try to find by Mongo _id first
        try:
            doc = self.repo.find_one(person_id)
            if doc:
                return doc
        except Exception:
            # find_one may raise if person_id is not a valid ObjectId; ignore and try userId lookup
            pass

        # fallback: try to find by userId field (some persons store the user id there)
        try:
            found = self.repo.find({"userId": person_id})
            if found:
                return found[0]
        except Exception:
            pass

        return None

    def update(self, person_id: str, updates: Dict[str, Any], actor_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # Capturar antes
        before = self.repo.find_one(person_id)
        updated = self.repo.update(person_id, updates)

        # Registrar historial de actualización
        try:
            db = get_mongo_db()
            history = db.get_collection("people_history")
            entry = {
                "person_id": str(person_id),
                "operation": "update",
                "actor": actor_id,
                "timestamp": datetime.utcnow(),
                "before": before,
                "after": updated,
                "changes": updates,
            }
            history.insert_one(entry)
        except Exception:
            pass

        # Sincronizar cambios relevantes con Neo4j (si corresponde)
        try:
            if not updated:
                return updated

            # Determinar id de nodo en Neo4j: preferimos userId si existe
            node_id = updated.get("userId") or updated.get("_id")
            if node_id:
                node_id = str(node_id)

                # Actualizar propiedades básicas del nodo
                nombre = updated.get("datosPersonales", {}).get("nombre") or updates.get("datosPersonales", {}).get("nombre")
                rol = updated.get("rol") or updates.get("rol")
                if nombre or rol:
                    self.graph_repo.create_person_node(person_id=node_id, nombre=nombre or "Desconocido", rol=rol or "Sin Rol")

                # Reconstruir habilidades si se enviaron en la actualización
                habilidades = []
                if "habilidades" in updates:
                    habilidades = updates.get("habilidades", [])
                elif "perfil" in updates and "skills" in updates["perfil"]:
                    habilidades = updates["perfil"]["skills"]

                if habilidades:
                    # eliminar relaciones previas y volver a vincular
                    try:
                        self.graph_repo.delete_person_skills(node_id)
                    except Exception:
                        pass

                    for skill in habilidades:
                        if isinstance(skill, str):
                            self.graph_repo.link_person_to_skill(person_id=node_id, skill_name=skill, nivel=1)
                        elif isinstance(skill, dict):
                            nombre_skill = skill.get("nombre")
                            nivel = skill.get("nivel", 1)
                            if nombre_skill:
                                self.graph_repo.link_person_to_skill(person_id=node_id, skill_name=nombre_skill, nivel=nivel)

        except Exception as e:
            print(f"⚠️ Error sincronizando actualización en Neo4j: {e}")

        return updated

    def delete(self, person_id: str, actor_id: Optional[str] = None) -> int:
        """
        Elimina una persona y registra el evento en people_history.
        Devuelve deleted_count (0 o 1).
        """
        # Capturar antes
        before = self.repo.find_one(person_id)
        deleted = self.repo.delete(person_id)

        try:
            db = get_mongo_db()
            history = db.get_collection("people_history")
            entry = {
                "person_id": str(person_id),
                "operation": "delete",
                "actor": actor_id,
                "timestamp": datetime.utcnow(),
                "before": before,
                "after": None,
            }
            history.insert_one(entry)
        except Exception:
            pass

        return deleted
        
    # Nota: historial registrado más abajo (none)

    # ==============================================
    # 🔗 CONEXIONES
    # ==============================================
    def connect(self, source_id: str, target_id: str, tipo: str = "amistad", direction: str = "two-way"):
        """
        Crea una conexión entre dos personas.
        - direction="one-way"  → (A)-[:TIPO]->(B)
        - direction="two-way"  → (A)-[:TIPO]->(B) y (B)-[:TIPO]->(A)
        """
        try:
            if direction == "one-way":
                self.graph_repo.create_connection_one_way(source_id, target_id, tipo)
            else:
                self.graph_repo.create_connection_two_way(source_id, target_id, tipo)

            # Record stats in Redis: increment connection counts for both participants
            try:
                record_connection(source_id, target_id)
            except Exception:
                pass

            return {
                "message": f"{source_id} conectado con {target_id}",
                "type": tipo.upper(),
                "direction": direction
            }

        except Exception as e:
            raise Exception(f"Error al conectar personas: {e}")

    def get_network(self, person_id: str):
        try:
            return self.graph_repo.get_network(person_id)
        except Exception as e:
            raise Exception(f"Error obteniendo red de conexiones: {e}")

    def get_common_connections(self, person_id: str, other_id: str):
        try:
            return self.graph_repo.get_common_connections(person_id, other_id)
        except Exception as e:
            raise Exception(f"Error obteniendo conexiones en común: {e}")

    def get_suggested_connections(self, person_id: str):
        try:
            return self.graph_repo.get_suggested_connections(person_id)
        except Exception as e:
            raise Exception(f"Error obteniendo sugerencias: {e}")

    def delete_connection(self, source_id: str, target_id: str, tipo: str = None):
        """
        Elimina una relación (o todas) entre dos personas.
        """
        try:
            deleted = self.graph_repo.delete_connection(source_id, target_id, tipo)
            if deleted == 0:
                return {"message": "No se encontraron relaciones para eliminar"}
            return {
                "message": f"Conexión eliminada entre {source_id} y {target_id}",
                "deletedCount": deleted,
                "type": tipo.upper() if tipo else "ALL"
            }
        except Exception as e:
            raise Exception(f"Error al eliminar conexión: {e}")

    def get_applications(self, person_id: str):
        """
        Devuelve todos los empleos a los que una persona se postuló.
        """
        try:
            return self.graph_repo.get_jobs_for_person(person_id)
        except Exception as e:
            raise Exception(f"Error obteniendo empleos postulados: {e}")
    
    def get_recommendations(self, person_id: str):
        """
        Devuelve empleos recomendados según las habilidades de la persona.
        """
        try:
            return self.graph_repo.get_job_recommendations(person_id)
        except Exception as e:
            raise Exception(f"Error obteniendo recomendaciones de empleos: {e}")

    def get_skills(self, person_id: str):
        """
        Devuelve las habilidades y niveles de una persona desde Neo4j.
        """
        try:
            return self.graph_repo.get_person_skills(person_id)
        except Exception as e:
            raise Exception(f"Error obteniendo habilidades: {e}")

    def get_people_by_skill(self, skill_name: str, min_level: int = 1):
        """
        Devuelve las personas que tienen una habilidad con un nivel mínimo.
        """
        try:
            return self.graph_repo.get_people_by_skill(skill_name, min_level)
        except Exception as e:
            raise Exception(f"Error obteniendo personas por habilidad: {e}")

    def get_history(self, person_id: str, limit: int = 100):
        """
        Recupera el historial de cambios para una persona desde la colección people_history.
        Devuelve los documentos ordenados por timestamp descendente.
        """
        try:
            db = get_mongo_db()
            history = db.get_collection("people_history")
            cursor = history.find({"person_id": str(person_id)}).sort("timestamp", -1).limit(limit)
            results = []
            for d in cursor:
                # serializar _id si existe
                if "_id" in d:
                    try:
                        d["_id"] = str(d["_id"])
                    except Exception:
                        pass
                results.append(d)
            return results
        except Exception as e:
            raise Exception(f"Error leyendo historial: {e}")
