# src/models/hiring.py
from typing import List, Dict, Optional
from datetime import datetime
from src.models.base import MongoBaseModel, Field

# Estructuras para Empleos [cite: 131]
class Requisitos(BaseModel):
    obligatorios: List[str] = Field(default_factory=list) # [cite: 141]
    deseables: List[str] = Field(default_factory=list) # [cite: 142]

class Empleo(MongoBaseModel):
    id: str = Field(alias="_id") # e.g., "em_2024_001" [cite: 134]
    empresaId: str # [cite: 135]
    publicadoPor: str # Persona ID [cite: 136]
    titulo: str
    area: str
    descripcion: str
    requisitos: Requisitos # [cite: 140]
    modalidad: str
    ubicacion: str
    estado: str = Field(description="abierto | pausado | cerrado") # [cite: 146]
    fechaPublicacion: datetime # [cite: 147]

    class Config(MongoBaseModel.Config):
        pass

# Estructuras para Postulaciones (Procesos de selección) [cite: 153]
class FeedbackPuntaje(BaseModel):
    autor: str # Persona ID [cite: 175]
    puntajes: Dict[str, float] # Ejemplo: {"tecnico": 8, "cultural": 7} [cite: 176]
    comentarios: str
    fecha: datetime # [cite: 178]

class Entrevista(BaseModel):
    tipo: str # tecnica, cultural, etc. [cite: 170]
    fecha: datetime # [cite: 171]
    evaluadores: List[str] # IDs de Personas [cite: 172]
    feedback: List[FeedbackPuntaje] = Field(default_factory=list) # [cite: 173]

class Oferta(BaseModel):
    estado: str = Field(description="pendiente | aceptada | rechazada | expirada") # [cite: 191]
    salario: Dict[str, float] # Ejemplo: {"monto": 2500, "moneda": "USD"} [cite: 192]
    enviadaEn: datetime # [cite: 193]
    decididaEn: Optional[datetime] = None # [cite: 194]

class Postulacion(MongoBaseModel):
    # _id es ObjectId() en el ejemplo [cite: 156]
    id: str = Field(alias="_id") 
    empresaId: str # [cite: 157]
    empleoId: str # [cite: 158]
    personaId: str # [cite: 159]
    estado: str = Field(description="preseleccion | entrevista | tecnica | propuesta | rechazo | contratado") # [cite: 162]
    historial: List[Dict] = Field(default_factory=list) # Auditoría de estados [cite: 164]
    entrevistas: List[Entrevista] = Field(default_factory=list) # [cite: 168]
    puntajeFinal: Optional[float] = None # Puntaje de afinidad/evaluación [cite: 189]
    oferta: Optional[Oferta] = None # [cite: 190]

    class Config(MongoBaseModel.Config):
        pass