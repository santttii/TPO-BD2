# src/models/base.py
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field

# Estructura anidada para habilidades, crucial para Neo4j y matching
class Habilidad(BaseModel):
    nombre: str
    nivel: int  # Nivel de dominio (e.g., 1 a 5) [cite: 97]

# Estructura anidada para ubicación
class Ubicacion(BaseModel):
    pais: Optional[str] = None # Ejemplo: "AR" [cite: 91]
    ciudad: Optional[str] = None # Ejemplo: "CABA" [cite: 91]

# Estructura base para todas las entidades con timestamps de MongoDB
class MongoBaseModel(BaseModel):
    creadoEn: datetime = Field(alias="creadoEn") # Mapea ISODate() [cite: 74]
    actualizadoEn: datetime = Field(alias="actualizadoEn") # Mapea ISODate() [cite: 75]
    
    class Config:
        # Permite la carga de datos con nombres de campo de MongoDB (ej. 'creadoEn')
        validate_by_name = True
        # Permite exportar el modelo como alias (útil para la API)
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }