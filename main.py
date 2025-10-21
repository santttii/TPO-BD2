# main.py (En la raíz del proyecto)

import os
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
from src.config.database import inicializar_conexiones 

# ⬅️ IMPORTACIÓN DE TODOS LOS ROUTERS
from src.api.routes.users import router as users_router
from src.api.routes.hiring import router as hiring_router 
from src.api.routes.learning import router as learning_router

# --- Inicialización ---

# 1. Cargar variables de entorno desde .env
load_dotenv()

# 2. Ejecutar las pruebas de conexión (opcional, pero útil al inicio)
inicializar_conexiones() 

# 3. Crear la instancia de FastAPI
app = FastAPI(
    title="Talentum+ Polyglot API",
    version="1.0.0",
    description="Plataforma Integral de Gestión de Talento IT."
)

# --- Rutas de Salud y Raíz ---

@app.get("/", tags=["Health"])
async def root():
    """Retorna el estado de la API."""
    return {"message": "API de Talentum+ is up and running."}

# ⬇️⬇️⬇️ INCLUSIÓN/REGISTRO DE MÓDULOS DE RUTAS ⬇️⬇️⬇️

app.include_router(users_router, prefix="/api/v1")
app.include_router(hiring_router, prefix="/api/v1")
app.include_router(learning_router, prefix="/api/v1")


# --- Inicio del Servidor ---
if __name__ == "__main__":
    # La variable de entorno TPO_PORT debe estar definida en .env si quieres usarla
    port = int(os.getenv("TPO_PORT", 8000))
    # El host es 0.0.0.0 para que sea accesible dentro de Docker
    uvicorn.run(app, host="0.0.0.0", port=port)