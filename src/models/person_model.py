from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class Skill(BaseModel):
    nombre: str
    nivel: int

class Experiencia(BaseModel):
    empresa: str
    rol: str
    desde: str
    hasta: Optional[str] = None

class Educacion(BaseModel):
    institucion: str
    titulo: str
    desde: int
    hasta: Optional[int] = None

# Payload de creación/actualización
class PersonIn(BaseModel):
    correo: str
    rol: str
    datosPersonales: Dict
    perfil: Dict
    experiencia: List[Experiencia] = []
    educacion: List[Educacion] = []
    intereses: List[str] = []
    conexiones: List[str] = []
    empresaActualId: Optional[str] = None

# Respuesta al cliente (incluye _id y timestamps)
class PersonOut(PersonIn):
    id: str = Field(alias="_id")
    versionActual: int = 1
    creadoEn: datetime
    actualizadoEn: datetime

    class Config:
        populate_by_name = True  # permite devolver alias "_id"
