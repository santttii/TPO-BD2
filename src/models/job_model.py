from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from bson import ObjectId


class Requisitos(BaseModel):
    obligatorios: List[str] = []
    deseables: List[str] = []


class JobIn(BaseModel):
    titulo: str
    descripcion: str
    ubicacion: str
    salario: float
    empresaId: str
    # Hacemos `requisitos` opcional y con valor por defecto vacio para evitar
    # errores de validación cuando existan jobs antiguos sin ese campo.
    requisitos: Optional[Requisitos] = Field(default_factory=Requisitos)


class JobOut(JobIn):
    id: Optional[str] = Field(default=None, alias="_id")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )
