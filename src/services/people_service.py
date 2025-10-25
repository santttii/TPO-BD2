from typing import Dict, Any, List, Optional
from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository


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
        return person



    def list(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.repo.find(filters)

    def get(self, person_id: str) -> Optional[Dict[str, Any]]:
        return self.repo.find_one(person_id)

    def update(self, person_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.repo.update(person_id, updates)

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
