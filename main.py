# main.py (raíz)
import os
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

from src.config.database import inicializar_conexiones
from src.api.routes.people_routes import router as people_router
from src.api.routes.company_routes import router as company_router
from src.api.routes.job_routes import router as job_router
from src.api.routes.auth_routes import router as auth_router
from src.api.middleware.session_middleware import session_middleware
from src.api.routes.course_routes import router as course_router
from src.api.routes.enrollment_routes import router as enrollment_router

load_dotenv()

try:
    inicializar_conexiones()
except Exception as e:
    print(f"⚠️ Error inicializando conexiones: {e}")

app = FastAPI(title="Talentum+ Polyglot API", version="1.0.0",
              description="Plataforma Integral de Gestión de Talento IT.")

# Registrar middleware de sesión (lee X-Session-Id y resuelve userId en Redis)
app.middleware("http")(session_middleware)

@app.get("/", tags=["Health"])
async def root():
    return {"message": "✅ API de Talentum+ is up and running."}

app.include_router(people_router, prefix="/api/v1")
app.include_router(company_router, prefix="/api/v1")  
app.include_router(job_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(course_router, prefix="/api/v1")
app.include_router(enrollment_router, prefix="/api/v1")


if __name__ == "__main__":
    port = int(os.getenv("TPO_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
