# Base image ligera de Python
FROM python:3.11-slim

WORKDIR /app

# Metadatos del autor
LABEL maintainer="Juan Andrés Covili Cabezas <juancovili@icloud.com>"
LABEL description="Retail Sales & Demand Analytics Pipeline (ETL, SQL, ML, AI Insights)"

# Copiar archivos de requerimientos y código
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY . .

# Variables de entorno
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Ejecutar tests automatizados al compilar
RUN python3 -m unittest discover tests

# Comando por defecto: ejecutar pipeline completo
CMD ["python3", "main.py"]
