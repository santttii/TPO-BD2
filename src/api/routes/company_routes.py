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
