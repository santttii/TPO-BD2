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
def create_person(person: PersonIn, request: Request):
    """
    Crea una persona vinculada al usuario en sesión.
    El middleware asigna `request.state.user_id` y aquí lo usamos como `userId`.
    """
    # Requiere sesión
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        person_data = person.model_dump()
        # Forzar vínculo con el usuario autenticado
        person_data["userId"] = request.state.user_id

        # Si ya existe una persona vinculada a este userId (se crea en /auth/register),
        # actualizamos ese documento en lugar de crear uno nuevo.
        existing = svc.list({"userId": request.state.user_id})
        if existing:
            # actualizar el primer documento encontrado
            existing_id = existing[0].get("_id")
            updated = svc.update(existing_id, person_data)
            return updated

        created = svc.create(person_data)
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[PersonOut])
def list_people():
    try:
        return svc.list({})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=PersonOut)
def get_person(request: Request):
    # Devuelve la persona vinculada al usuario en sesión
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    found = svc.list({"userId": request.state.user_id})
    if not found:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return found[0]


@router.put("/me", response_model=PersonOut)
def update_person(updates: Dict[str, Any], request: Request):
    # Requiere sesión
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    found = svc.list({"userId": request.state.user_id})
    if not found:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    target_id = found[0].get("_id")

    updated = svc.update(target_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return updated


@router.delete("/me")
def delete_person(request: Request):
    # Requiere sesión
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    found = svc.list({"userId": request.state.user_id})
    if not found:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    target_id = found[0].get("_id")

    try:
        if hasattr(svc, "delete"):
            svc.delete(target_id)
            return {"message": "Persona eliminada correctamente"}
        else:
            raise Exception("Delete operation not implemented on PeopleService")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===============================================
# 🔗 CONEXIONES (Neo4j)
# ===============================================

@router.post("/me/connections/{target_id}")
def connect_people(
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

    try:
        tipo = body.get("type", "amistad")
        source_id = request.state.user_id
        result = svc.connect(source_id, target_id, tipo, direction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me/recommendations")
def get_recommendations(request: Request = None):
    """
    Obtiene empleos recomendados para una persona según sus habilidades.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        pid = request.state.user_id
        recs = svc.get_recommendations(pid)
        return {"personId": pid, "recommendations": recs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me/network")
def get_network(request: Request = None):
    """
    Devuelve la red (conexiones) de una persona.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        pid = request.state.user_id
        network = svc.get_network(pid)
        return {"personId": pid, "connections": network}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me/connections/common/{other_id}")
def get_common_connections(other_id: str, request: Request = None):
    """
    Devuelve las conexiones en común entre dos personas.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        pid = request.state.user_id
        # if other_id == 'me', map to session user id
        if other_id == "me":
            other_id = request.state.user_id
        commons = svc.get_common_connections(pid, other_id)
        return {"person1": pid, "person2": other_id, "commonConnections": commons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me/connections/suggested")
def get_suggested_connections(request: Request = None):
    """
    Devuelve sugerencias de conexión (segundo grado de relación).
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        pid = request.state.user_id
        suggested = svc.get_suggested_connections(pid)
        return {"personId": pid, "suggestedConnections": suggested}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/me/connections/{target_id}")
def delete_connection(target_id: str, type: str = Query(None, description="Tipo de conexión opcional"), request: Request = None):
    """
    Elimina una conexión entre dos personas.
    - Si se pasa ?type=MENTORSHIP → elimina solo ese tipo.
    - Si no se pasa, elimina todas las relaciones entre ambos.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        pid = request.state.user_id
        result = svc.delete_connection(pid, target_id, type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me/applications")
def get_applications(request: Request = None):
    """
    Devuelve los empleos a los que una persona se postuló.
    """
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        pid = request.state.user_id
        apps = svc.get_applications(pid)
        return {"personId": pid, "applications": apps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me/jobs/recommendations", tags=["People"])
def get_job_recommendations(request: Request):
    """
    Retorna los empleos más afines según las habilidades de la persona.
    """
    try:
        service = PeopleService()
        uid = request.state.user_id
        recommendations = service.get_recommendations(uid)
        return {"person_id": uid, "recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me/skills")
def get_person_skills(request: Request):
    """
    Obtiene todas las habilidades de una persona (con su nivel) desde Neo4j.
    """
    try:
        pid = request.state.user_id
        skills = svc.get_skills(pid)
        return {"personId": pid, "skills": skills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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


@router.get("/{person_id}", response_model=PersonOut)
def get_person_by_id(person_id: str, request: Request):
    """
    Devuelve la información de una persona por su ID (similar a /me).
    Requiere autenticación. Cada vez que se consulta esta ruta se incrementa
    la stat de 'profile views' para la persona consultada (registrado en Redis).
    """
    # Requiere sesión
    if not getattr(request, "state", None) or not request.state.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        person = svc.get(person_id)
        if not person:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
        return person
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
