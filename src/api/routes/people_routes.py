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

@router.get("/{person_id}/connections/common/{other_id}")
def get_common_connections(person_id: str, other_id: str):
    """
    Devuelve las conexiones en común entre dos personas.
    """
    try:
        commons = svc.get_common_connections(person_id, other_id)
        return {"person1": person_id, "person2": other_id, "commonConnections": commons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/connections/suggested")
def get_suggested_connections(person_id: str):
    """
    Devuelve sugerencias de conexión (segundo grado de relación).
    """
    try:
        suggested = svc.get_suggested_connections(person_id)
        return {"personId": person_id, "suggestedConnections": suggested}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import Query

@router.delete("/{person_id}/connections/{target_id}")
def delete_connection(person_id: str, target_id: str, type: str = Query(None, description="Tipo de conexión opcional")):
    """
    Elimina una conexión entre dos personas.
    - Si se pasa ?type=MENTORSHIP → elimina solo ese tipo.
    - Si no se pasa, elimina todas las relaciones entre ambos.
    """
    try:
        result = svc.delete_connection(person_id, target_id, type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/applications")
def get_applications(person_id: str):
    """
    Devuelve los empleos a los que una persona se postuló.
    """
    try:
        apps = svc.get_applications(person_id)
        return {"personId": person_id, "applications": apps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/people/{person_id}/recommendations", tags=["People"])
def get_job_recommendations(person_id: str):
    """
    Retorna los empleos más afines según las habilidades de la persona.
    """
    try:
        service = PeopleService()
        recommendations = service.get_recommendations(person_id)
        return {"person_id": person_id, "recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
