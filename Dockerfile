# Dockerfile limpio
FROM python:3.11-slim

# 1. Establece el directorio de trabajo base. Los comandos se ejecutan desde /app
WORKDIR /app

# 2. Copia e instala requisitos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copia los archivos de código fuente a /app dentro del contenedor
# Copia la carpeta src/ a /app/src
COPY src/ /app/src 
# Copia main.py a /app/main.py
COPY main.py .
# Copia .env a /app/.env
COPY .env .

# 4. Configura el entorno Python para que las importaciones funcionen correctamente
ENV PYTHONPATH=/app

# 5. Comando de inicio
CMD ["python", "main.py"]