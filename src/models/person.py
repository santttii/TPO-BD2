# src/models/person.py
from typing import List, Optional, Dict
from src.models.base import MongoBaseModel, Habilidad, Ubicacion, Field
from pydantic import BaseModel, Field

class DatosPersonales(BaseModel):
    nombre: str # Ejemplo: "Juan Rodríguez" [cite: 89]
    telefono: Optional[str] = None
    ubicacion: Ubicacion # Estructura anidada [cite: 91]

class Perfil(BaseModel):
    titulo: Optional[str] = None # Ejemplo: "Backend Developer" [cite: 94]
    resumen: Optional[str] = None
    habilidades: List[Habilidad] = Field(default_factory=list) # Clave para Neo4j [cite: 96]
    intereses: List[str] = Field(default_factory=list) # Clave para recomendaciones [cite: 100]

class ExperienciaLaboral(BaseModel):
    empresa: str
    rol: str
    desde: str # Formato "YYYY-MM" [cite: 103]
    hasta: Optional[str] = None

class Educacion(BaseModel):
    institucion: str
    titulo: str
    desde: int
    hasta: int

class Person(MongoBaseModel):
    id: str = Field(alias="_id") # Se usa un string (e.g., "p_456") [cite: 83]
    correo: str
    passwordHash: Optional[str] = None # [cite: 85]
    rol: str = Field(description="talento | empresa | mentor | admin") # [cite: 86]
    
    datosPersonales: DatosPersonales # Documento anidado [cite: 88]
    perfil: Perfil # Documento anidado [cite: 93]
    experiencia: List[ExperienciaLaboral] = Field(default_factory=list) # [cite: 102]
    educacion: List[Educacion] = Field(default_factory=list) # [cite: 105]
    
    empresaActualId: Optional[str] = None # FK a empresas [cite: 108]
    versionActual: int = 1 # [cite: 109]
    conexiones: List[str] = Field(default_factory=list) # IDs de otras personas [cite: 110]
    
    class Config(MongoBaseModel.Config):
        pass # Hereda configuración de MongoBaseModel