from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from src.models.person_model import PersonIn, PersonOut
from src.models.connection_model import ConnectionIn
from src.services.people_service import PeopleService

router = APIRouter(prefix="/people", tags=["People"])
svc = PeopleService()

# ===============================================
# 👤 CRUD
# ===============================================

@router.post("/", response_model=PersonOut)
def create_person(person: PersonIn):
    try:
        created = svc.create(person.model_dump())
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[PersonOut])
def list_people():
    try:
        return svc.list({})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{person_id}", response_model=PersonOut)
def get_person(person_id: str):
    person = svc.get(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return person


@router.put("/{person_id}", response_model=PersonOut)
def update_person(person_id: str, updates: Dict[str, Any]):
    updated = svc.update(person_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return updated


@router.delete("/{person_id}")
def delete_person(person_id: str):
    try:
        svc.delete(person_id)
        return {"message": "Persona eliminada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===============================================
# 🔗 CONEXIONES (Neo4j)
# ===============================================

@router.post("/{person_id}/connections/{target_id}")
def connect_people(
    person_id: str,
    target_id: str,
    body: Dict[str, str],
    direction: str = Query("two-way", description="Tipo de conexión: one-way o two-way"),
):
    """
    Crea una conexión entre dos personas.
    direction=one-way → (A)-[:TIPO]->(B)
    direction=two-way → (A)-[:TIPO]->(B) y (B)-[:TIPO]->(A)
    """
    try:
        tipo = body.get("type", "amistad")
        result = svc.connect(person_id, target_id, tipo, direction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{person_id}/recommendations")
def get_recommendations(person_id: str):
    """
    Obtiene empleos recomendados para una persona según sus habilidades.
    """
    try:
        recs = svc.get_recommendations(person_id)
        return {"personId": person_id, "recommendations": recs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/network")
def get_network(person_id: str):
    """
    Devuelve la red (conexiones) de una persona.
    """
    try:
        network = svc.get_network(person_id)
        return {"personId": person_id, "connections": network}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
