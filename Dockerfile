FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiá explícitamente main.py y la carpeta src
COPY ./main.py /app/main.py
COPY ./src /app/src

# 🔑 hace visible /app y /app/src para los imports 'src.*'
ENV PYTHONPATH=/app:/app/src

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
