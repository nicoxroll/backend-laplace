# Ejemplo de Dockerfile optimizado
FROM python:3.10-slim

# Instalar dependencias del sistema primero
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar grupos de dependencias por separado para mejor caché
COPY requirements-base.txt .
RUN pip install --no-cache-dir -r requirements-base.txt

COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt

COPY requirements-doc.txt .
RUN pip install --no-cache-dir -r requirements-doc.txt

# Copiar el resto del código
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]