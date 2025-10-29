from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any
from src.models.company_model import CompanyIn, CompanyOut
from src.services.company_service import CompanyService
from bson import ObjectId

router = APIRouter(prefix="/companies", tags=["Companies"])
svc = CompanyService()

@router.post("/", response_model=CompanyOut)
def create_company(company: CompanyIn, request: Request):
    """Crea una empresa y la vincula al usuario autenticado en `created_by`."""
    user_id = getattr(getattr(request, "state", None), "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        data = company.model_dump()
        data["created_by"] = str(user_id)

        created = svc.create(data)

        # serializar _id si es ObjectId
        if "_id" in created and isinstance(created["_id"], ObjectId):
            created["_id"] = str(created["_id"])

        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[CompanyOut])
def list_companies(request: Request):
    """Lista las empresas del usuario autenticado (usa session middleware para resolver user_id)."""
    user_id = getattr(getattr(request, "state", None), "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        items = svc.list(str(user_id))
        # asegurar que los _id estén serializados
        for doc in items:
            if "_id" in doc and isinstance(doc["_id"], ObjectId):
                doc["_id"] = str(doc["_id"])
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: str, request: Request):
    """Obtiene una empresa solo si el usuario autenticado es su creador."""
    user_id = getattr(getattr(request, "state", None), "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        company = svc.get(company_id, str(user_id))
        if not company:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        return company
    except PermissionError:
        raise HTTPException(status_code=403, detail="No autorizado para ver esta empresa")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: str, updates: Dict[str, Any], request: Request):
    """Actualiza una empresa solo si el usuario autenticado es su creador."""
    user_id = getattr(getattr(request, "state", None), "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        updated = svc.update(company_id, updates, str(user_id))
        if not updated:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        return updated
    except PermissionError:
        raise HTTPException(status_code=403, detail="No autorizado para modificar esta empresa")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{company_id}")
def delete_company(company_id: str, request: Request):
    """Elimina una empresa solo si el usuario autenticado es su creador."""
    user_id = getattr(getattr(request, "state", None), "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        deleted = svc.delete(company_id, str(user_id))
        if not deleted:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        return {"message": "Empresa eliminada correctamente"}
    except PermissionError:
        raise HTTPException(status_code=403, detail="No autorizado para eliminar esta empresa")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/{company_a}/partners/{company_b}")
def link_companies(company_a: str, company_b: str, body: Dict[str, str]):
    try:
        tipo = body.get("type", "PARTNER_DE")
        return svc.link_partner(company_a, company_b, tipo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{company_id}/employees/{person_id}")
def link_employee(company_id: str, person_id: str, body: Dict[str, str]):
    try:
        role = body.get("role", "TRABAJA_EN")
        return svc.link_person(person_id, company_id, role)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
