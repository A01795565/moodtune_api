# Dockerfile
FROM python:3.11-slim

# Evitar bytecode y usar salida sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Crear directorio de la app
WORKDIR /app

# Dependencias del sistema (opcional, útiles para mysql-connector)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copiar dependencias de Python
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . /app

# Variables de entorno por defecto (se pueden sobreescribir en compose)
ENV DB_HOST=db \
    DB_PORT=3306 \
    DB_USER=moodTuneTest \
    DB_PASSWORD=StrongPassword123! \
    DB_NAME=moodtune \
    DEBUG=false

# Exponer puerto del servicio
EXPOSE 8000

# Comando de arranque (Gunicorn productivo) — alternativamente flask dev server
# CMD ["python", "run.py"]
CMD ["python", "run.py"]
