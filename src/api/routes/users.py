# src/api/routes/users.py
from typing import List, Optional
from fastapi import APIRouter, Body, HTTPException, status
from src.services.user_service import UserService 
# Importamos los modelos para tipificar la entrada y salida de la API
from src.models.person import Person, Perfil, DatosPersonales

router = APIRouter(
    prefix="/users",
    tags=["People & Profiles"]
)

user_service = UserService() 

# ----------------------------------------------------
# 🟢 GET: Obtener Perfil (Lectura AP/Cache)
# ----------------------------------------------------
@router.get(
    "/{user_id}", 
    response_model=Person, # Tipifica la respuesta usando el modelo Person
    status_code=status.HTTP_200_OK
)
async def get_user_profile(user_id: str):
    """
    RF 1: Retorna el perfil completo de un usuario. Utiliza Redis (AP) y Mongo (CP).
    """
    profile_data = user_service.get_profile(user_id)
    
    if profile_data is None:
        raise HTTPException(status_code=404, detail="User not found")
        
    return profile_data # FastAPI serializa el dict/modelo a JSON

# ----------------------------------------------------
# 🟢 POST: Crear/Sincronizar Perfil (Escritura Políglota)
# ----------------------------------------------------
@router.post(
    "/", 
    # FastAPI usa Person como validador de entrada (Request Body)
    response_model=Person, 
    status_code=status.HTTP_201_CREATED
)
async def create_new_user(person: Person = Body(...)):
    """
    Crea un nuevo perfil en MongoDB (CP) y sincroniza los nodos en Neo4j (AP).
    """
    # La validación de tipos y estructura la hace Pydantic automáticamente.
    try:
        # Pasa la instancia validada del modelo al servicio
        new_user = user_service.create_new_profile(person.dict(by_alias=True))
        return new_user
    except Exception as e:
        # En un caso real, manejar errores de unicidad de correo (Mongo) o fallos de sincronización
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

# ----------------------------------------------------
# 🟢 PATCH: Actualizar Perfil (Escritura Políglota)
# ----------------------------------------------------
@router.patch("/{user_id}/profile", response_model=dict, status_code=status.HTTP_200_OK)
async def update_user_profile(user_id: str, updates: dict = Body(...)):
    """
    Actualiza datos en MongoDB (CP) y dispara la sincronización a Neo4j e invalidación de caché (Redis).
    """
    # En este caso, updates es un dict genérico que valida la estructura.
    try:
        result = user_service.update_profile(user_id, updates)
        return {"message": "Profile updated and synchronization triggered.", "details": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}/history")
async def get_profile_version_history(user_id: str):
    """
    RF 1: Retorna el historial de versiones/cambios del perfil.
    Fuente: MongoDB (colección versiones_persona).
    """
    # Lógica: user_service.get_version_history(user_id)
    return {"user_id": user_id, "message": "Historial de versiones (MongoDB)."}

@router.get("/{user_id}/recommendations")
async def get_user_recommendations(user_id: str):
    """
    RF 5: Retorna recomendaciones personalizadas (empleos, cursos, mentores).
    Fuente: Neo4j (grafos de interés y redes)[cite: 293].
    """
    recommendations = user_service.get_recommendations(user_id)
    return {"status": "success", "data": recommendations}