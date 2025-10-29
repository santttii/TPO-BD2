from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any
from bson import ObjectId

from src.models.company_model import CompanyIn, CompanyOut
from src.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["Companies"])
svc = CompanyService()


# ==============================
# Helpers
# ==============================
def _require_auth(request: Request) -> str:
    """Obtiene el user_id desde el middleware o lanza 401."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return str(user_id)


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


# ==============================
# Endpoints
# ==============================

@router.post("/", response_model=CompanyOut)
def create_company(company: CompanyIn, request: Request):
    """Crea una empresa y la vincula al usuario autenticado."""
    user_id = _require_auth(request)

    # Armamos el diccionario base
    data = company.model_dump()
    data["created_by"] = str(user_id)

    try:
        created = svc.create(data)
        return _serialize(created)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating company: {e}")


@router.get("/", response_model=List[CompanyOut])
def list_companies(request: Request):
    """Lista las empresas del usuario autenticado."""
    user_id = _require_auth(request)
    try:
        items = svc.list(user_id)
        return [_serialize(doc) for doc in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing companies: {e}")


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: str, request: Request):
    """Obtiene una empresa si pertenece al usuario."""
    user_id = _require_auth(request)
    company = svc.get(company_id, user_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return _serialize(company)


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: str, updates: Dict[str, Any], request: Request):
    """Actualiza una empresa si es del usuario autenticado."""
    user_id = _require_auth(request)
    try:
        updated = svc.update(company_id, updates, user_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Empresa no encontrada o sin permisos")
        return _serialize(updated)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating company: {e}")


@router.delete("/{company_id}")
def delete_company(company_id: str, request: Request):
    """Elimina una empresa si es del usuario autenticado."""
    user_id = _require_auth(request)
    try:
        deleted = svc.delete(company_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Empresa no encontrada o sin permisos")
        return {"message": "Empresa eliminada correctamente"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting company: {e}")
    
@router.post("/{company_a}/partners/{company_b}")
def link_companies(company_a: str, company_b: str, body: Dict[str, str]):
    """
    Crea una relación de partnership siempre en ambos sentidos entre company_a y company_b.
    Esto fuerza que exista (A)-[:TYPE]->(B) y (B)-[:TYPE]->(A).
    """
    try:
        tipo = body.get("type", "PARTNER_DE")
        # Crear ambas direcciones (best-effort; no queremos que una falla impida la otra)
        res_ab = None
        res_ba = None
        try:
            res_ab = svc.link_partner(company_a, company_b, tipo)
        except Exception as e:
            # registrar y continuar
            res_ab = {"warning": f"Could not link {company_a} -> {company_b}: {e}"}

        try:
            res_ba = svc.link_partner(company_b, company_a, tipo)
        except Exception as e:
            res_ba = {"warning": f"Could not link {company_b} -> {company_a}: {e}"}

        return {"a_to_b": res_ab, "b_to_a": res_ba}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{company_id}/employees/me")
def link_employee(company_id: str, body: Dict[str, str], request: Request):
    """
    Vincula al usuario autenticado como empleado de la empresa.
    Usa el user_id obtenido por el middleware (request.state.user_id) en lugar
    de recibir un person_id en la URL.
    """
    # Requiere sesión
    user_id = _require_auth(request)

    try:
        role = body.get("role", "TRABAJA_EN")
        return svc.link_person(user_id, company_id, role)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
