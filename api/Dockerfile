# Dockerfile optimizado con un solo requirements.txt
FROM python:3.10-slim

# Instalar dependencias del sistema primero
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar solo el archivo de requisitos primero para mejor uso de caché
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Verificar salud
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]