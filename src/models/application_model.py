from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class EstadoItem(BaseModel):
    estado: str
    fecha: datetime = Field(default_factory=datetime.utcnow)
    observacion: Optional[str] = None


class FeedbackItem(BaseModel):
    autor: str
    comentario: str
    fecha: datetime = Field(default_factory=datetime.utcnow)


class Oferta(BaseModel):
    salario: Optional[float] = None
    modalidad: Optional[str] = None
    fecha_envio: datetime = Field(default_factory=datetime.utcnow)
    comentario: Optional[str] = None


class ApplicationIn(BaseModel):
    person_id: str
    job_id: str
    estado_actual: str = "postulado"
    historial_estados: List[EstadoItem] = Field(default_factory=lambda: [EstadoItem(estado="postulado")])
    feedback: Optional[List[FeedbackItem]] = []
    oferta: Optional[Oferta] = None


class ApplicationOut(ApplicationIn):
    id: Optional[str] = Field(default=None, alias="_id")
    creadoEn: datetime = Field(default_factory=datetime.utcnow)
    actualizadoEn: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        populate_by_name = True
