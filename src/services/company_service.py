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
        company = self.repo.create(payload)
        company["_id"] = str(company["_id"])

        # Sincronizar en Neo4j
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
    # 📋 LIST (GET all)
    # ===============================================================
    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        companies = self.repo.find(filters or {})
        for c in companies:
            c["_id"] = str(c["_id"])
        return companies

    # ===============================================================
    # 🔎 GET BY ID
    # ===============================================================
    def get(self, company_id: str) -> Optional[Dict[str, Any]]:
        company = self.repo.find_one(company_id)
        if company:
            company["_id"] = str(company["_id"])
        return company

    # ===============================================================
    # ✏️ UPDATE
    # ===============================================================
    def update(self, company_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Actualiza los campos indicados de una empresa.
        Ejemplo:
            PUT /companies/68f96...  con body {"pais": "Uruguay"}
        """
        updated = self.repo.update(company_id, updates)
        if updated:
            updated["_id"] = str(updated["_id"])

            # Si cambian datos clave, actualizar también en Neo4j
            try:
                nombre = updates.get("nombre", updated.get("nombre", ""))
                industria = updates.get("industria", updated.get("industria", ""))
                self.graph_repo.create_company_node(company_id, nombre, industria)
            except Exception as e:
                print(f"⚠️ Error actualizando nodo Company en Neo4j: {e}")

        return updated

    # ===============================================================
    # 🗑️ DELETE
    # ===============================================================
    def delete(self, company_id: str) -> bool:
        """
        Elimina una empresa por ID (Mongo). En Neo4j podrías eliminar su nodo también.
        """
        deleted = self.repo.delete(company_id)
        if deleted:
            try:
                # Eliminamos nodo de Neo4j también
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
