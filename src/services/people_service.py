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
        person = self.repo.create(payload)
        try:
            self.graph_repo.create_person_node(
                person_id=str(person["_id"]),
                name=payload["datosPersonales"]["nombre"],
                role=payload["rol"]
            )
        except Exception as e:
            print(f"⚠️ Error creando nodo en Neo4j: {e}")
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
