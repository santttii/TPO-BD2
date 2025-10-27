from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any
from src.models.company_model import CompanyIn, CompanyOut
from src.services.company_service import CompanyService
from bson import ObjectId

router = APIRouter(prefix="/companies", tags=["Companies"])
svc = CompanyService()

@router.post("/", response_model=CompanyOut)
def create_company(company: CompanyIn):
    try:
        # 1. Obtiene el diccionario de la compañía creada, que incluye el ObjectId
        created = svc.create(company.model_dump())
        
        # 🟢 CORRECCIÓN: Convierte el ObjectId a str para cumplir con CompanyOut
        # Esto previene el ResponseValidationError
        if "_id" in created and isinstance(created["_id"], ObjectId):
             created["_id"] = str(created["_id"])
        
        # 2. Retorna el diccionario, ahora con el _id serializado como str
        return created 
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[CompanyOut])
def list_companies():
    try:
        return svc.list({})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: str):
    company = svc.get(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company

@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: str, updates: Dict[str, Any]):
    updated = svc.update(company_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return updated

@router.delete("/{company_id}")
def delete_company(company_id: str):
    deleted = svc.delete(company_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return {"message": "Empresa eliminada correctamente"}



@router.post("/{company_a}/partners/{company_b}")
def link_companies(company_a: str, company_b: str, body: Dict[str, str]):
    try:
        tipo = body.get("type", "PARTNER_DE")
        return svc.link_partner(company_a, company_b, tipo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{company_id}/employees/{person_id}")
def link_employee(company_id: str, person_id: str, body: Dict[str, str], request: Request):
    """
    Vincula la persona autenticada a la empresa. Requiere sesión válida.
    - Si no viene sesión -> 401
    - Si el person_id en la URL no coincide con la sesión -> 403
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if person_id and person_id != request.state.user_id:
        raise HTTPException(status_code=403, detail="Session user mismatch")

    try:
        role = body.get("role", "TRABAJA_EN")
        return svc.link_person(request.state.user_id, company_id, role)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
