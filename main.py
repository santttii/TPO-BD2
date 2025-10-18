# main.py (En la raíz del proyecto)

import os
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
# Importamos la función de prueba de conexiones
from src.config.database import inicializar_conexiones 

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

# --- Importación de Módulos de Rutas (Endpoints) ---

# Pendiente: Importar los routers de users, orders, analytics.
# from src.api.routes.users import router as users_router
# app.include_router(users_router, prefix="/api/v1")


# --- Inicio del Servidor ---
if __name__ == "__main__":
    # La variable de entorno TPO_PORT debe estar definida en .env si quieres usarla
    port = int(os.getenv("TPO_PORT", 8000))
    # El host es 0.0.0.0 para que sea accesible dentro de Docker
    uvicorn.run(app, host="0.0.0.0", port=port)