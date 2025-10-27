from fastapi import APIRouter, HTTPException, Query, Request
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
    request: Request = None,
):
    """
    Crea una conexión entre dos personas.
    direction=one-way → (A)-[:TIPO]->(B)
    direction=two-way → (A)-[:TIPO]->(B) y (B)-[:TIPO]->(A)
    """
    # Requiere sesión: obligamos a que exista request.state.user_id
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Si se pasó person_id en la URL, debe coincidir con la sesión (evita spoofing)
    if person_id and person_id != request.state.user_id:
        raise HTTPException(status_code=403, detail="Session user mismatch")

    try:
        tipo = body.get("type", "amistad")
        source_id = request.state.user_id
        result = svc.connect(source_id, target_id, tipo, direction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{person_id}/recommendations")
def get_recommendations(person_id: str, request: Request = None):
    """
    Obtiene empleos recomendados para una persona según sus habilidades.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if person_id and person_id != request.state.user_id:
        raise HTTPException(status_code=403, detail="Session user mismatch")

    try:
        pid = request.state.user_id
        recs = svc.get_recommendations(pid)
        return {"personId": pid, "recommendations": recs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/network")
def get_network(person_id: str, request: Request = None):
    """
    Devuelve la red (conexiones) de una persona.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if person_id and person_id != request.state.user_id:
        raise HTTPException(status_code=403, detail="Session user mismatch")

    try:
        pid = request.state.user_id
        network = svc.get_network(pid)
        return {"personId": pid, "connections": network}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/connections/common/{other_id}")
def get_common_connections(person_id: str, other_id: str, request: Request = None):
    """
    Devuelve las conexiones en común entre dos personas.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if person_id and person_id != request.state.user_id:
        raise HTTPException(status_code=403, detail="Session user mismatch")

    try:
        pid = request.state.user_id
        commons = svc.get_common_connections(pid, other_id)
        return {"person1": pid, "person2": other_id, "commonConnections": commons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/connections/suggested")
def get_suggested_connections(person_id: str, request: Request = None):
    """
    Devuelve sugerencias de conexión (segundo grado de relación).
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if person_id and person_id != request.state.user_id:
        raise HTTPException(status_code=403, detail="Session user mismatch")

    try:
        pid = request.state.user_id
        suggested = svc.get_suggested_connections(pid)
        return {"personId": pid, "suggestedConnections": suggested}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{person_id}/connections/{target_id}")
def delete_connection(person_id: str, target_id: str, type: str = Query(None, description="Tipo de conexión opcional"), request: Request = None):
    """
    Elimina una conexión entre dos personas.
    - Si se pasa ?type=MENTORSHIP → elimina solo ese tipo.
    - Si no se pasa, elimina todas las relaciones entre ambos.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if person_id and person_id != request.state.user_id:
        raise HTTPException(status_code=403, detail="Session user mismatch")

    try:
        pid = request.state.user_id
        result = svc.delete_connection(pid, target_id, type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{person_id}/applications")
def get_applications(person_id: str, request: Request = None):
    """
    Devuelve los empleos a los que una persona se postuló.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if person_id and person_id != request.state.user_id:
        raise HTTPException(status_code=403, detail="Session user mismatch")

    try:
        pid = request.state.user_id
        apps = svc.get_applications(pid)
        return {"personId": pid, "applications": apps}
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

@router.get("/{person_id}/skills")
def get_person_skills(person_id: str):
    """
    Obtiene todas las habilidades de una persona (con su nivel) desde Neo4j.
    """
    try:
        skills = svc.get_skills(person_id)
        return {"personId": person_id, "skills": skills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import Query

@router.get("/skills/{skill_name}/people")
def get_people_by_skill(skill_name: str, min_level: int = Query(1, ge=1, le=5, description="Nivel mínimo (1-5)")):
    """
    Devuelve todas las personas que poseen la habilidad indicada con un nivel mínimo.
    Ejemplo: /api/v1/people/skills/Python/people?min_level=3
    """
    try:
        people = svc.get_people_by_skill(skill_name, min_level)
        return {
            "skill": skill_name,
            "min_level": min_level,
            "count": len(people),
            "people": people
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
