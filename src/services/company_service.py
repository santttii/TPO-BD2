from typing import Dict, Any, List, Optional
from src.repositories.mongo_repository import MongoRepository
from src.repositories.neo4j_repository import Neo4jRepository


class CompanyService:
    def __init__(self):
        # Mongo (colección principal)
        self.repo = MongoRepository("companies")
        # Neo4j (grafo)
        self.graph_repo = Neo4jRepository()

    # ===============================================================
    # 🏗️ CREATE
    # ===============================================================
    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea una empresa en Mongo y su nodo en Neo4j.
        El payload debe incluir 'created_by' (user_id) desde el router.
        """
        company = self.repo.create(payload)
        company["_id"] = str(company["_id"])

        # Crear nodo en Neo4j
        try:
            self.graph_repo.create_company_node(
                company_id=company["_id"],
                nombre=payload["nombre"],
                industria=payload["industria"],
            )
        except Exception as e:
            print(f"⚠️ Error creando nodo Company en Neo4j: {e}")

        return company

    # ===============================================================
    # 📋 LIST (solo empresas del usuario)
    # ===============================================================
    def list(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retorna las empresas creadas por el usuario autenticado.
        """
        companies = self.repo.find({"created_by": user_id})
        for c in companies:
            c["_id"] = str(c["_id"])
        return companies

    # ===============================================================
    # 🔎 GET BY ID (solo si es dueño)
    # ===============================================================
    def get(self, company_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        company = self.repo.find_one(company_id)
        if company:
            company["_id"] = str(company["_id"])
            if user_id and company.get("created_by") != user_id:
                raise PermissionError("Not authorized to access this company")
        return company

    # ===============================================================
    # ✏️ UPDATE (solo si es dueño)
    # ===============================================================
    def update(self, company_id: str, updates: Dict[str, Any], user_id: str) -> Optional[Dict[str, Any]]:
        company = self.repo.find_one(company_id)
        if not company:
            return None
        if company.get("created_by") != user_id:
            raise PermissionError("Not authorized to modify this company")

        updated = self.repo.update(company_id, updates)
        if updated:
            updated["_id"] = str(updated["_id"])

            # Actualizar también en Neo4j si cambia nombre o industria
            try:
                nombre = updates.get("nombre", updated.get("nombre", ""))
                industria = updates.get("industria", updated.get("industria", ""))
                self.graph_repo.create_company_node(company_id, nombre, industria)
            except Exception as e:
                print(f"⚠️ Error actualizando nodo Company en Neo4j: {e}")

        return updated

    # ===============================================================
    # 🗑️ DELETE (solo si es dueño)
    # ===============================================================
    def delete(self, company_id: str, user_id: str) -> bool:
        company = self.repo.find_one(company_id)
        if not company:
            return False
        if company.get("created_by") != user_id:
            raise PermissionError("Not authorized to delete this company")

        deleted = self.repo.delete(company_id)
        if deleted:
            try:
                self.graph_repo.delete_node_by_id(company_id, label="Company")
            except Exception as e:
                print(f"⚠️ Error eliminando nodo Company en Neo4j: {e}")
        return deleted

    # ===============================================================
    # 🧩 RELACIÓN PERSONA → COMPANY
    # ===============================================================
    def link_person(self, person_id: str, company_id: str, role: str = "TRABAJA_EN"):
        """
        Crea una relación (Person)-[:TRABAJA_EN]->(Company)
        """
        try:
            self.graph_repo.link_person_to_company(person_id, company_id, role)
            return {
                "message": f"Persona {person_id} vinculada a empresa {company_id}",
                "type": role,
            }
        except Exception as e:
            raise Exception(f"Error vinculando persona a empresa: {e}")

    # ===============================================================
    # 🧩 RELACIÓN COMPANY ↔ COMPANY
    # ===============================================================
    def link_partner(self, company_a: str, company_b: str, tipo: str = "PARTNER_DE"):
        """
        Crea una relación (CompanyA)-[:PARTNER_DE]->(CompanyB)
        """
        try:
            self.graph_repo.link_company_to_company(company_a, company_b, tipo)
            return {
                "message": f"Empresas {company_a} y {company_b} vinculadas ({tipo})",
                "type": tipo,
            }
        except Exception as e:
            raise Exception(f"Error vinculando empresas: {e}")
