# @project   Retail Sales & Demand Analytics Pipeline
# @author    Juan Covili <https://github.com/juanCovili>
# @repo      https://github.com/juanCovili/retail-sales-etl-pipeline
# @portfolio https://juancovili.com
# @copyright Copyright (c) 2026 Juan Covili. Todos los derechos reservados.
# Base image ligera de Python
FROM python:3.11-slim

WORKDIR /app

# Metadatos del autor
LABEL maintainer="Juan Covili <https://github.com/juanCovili>"
LABEL description="Retail Sales & Demand Analytics Pipeline (ETL, SQL, ML, AI Insights)"
LABEL org.opencontainers.image.authors="Juan Covili <https://github.com/juanCovili>"
LABEL org.opencontainers.image.url="https://juancovili.com"
LABEL org.opencontainers.image.source="https://github.com/juanCovili/retail-sales-etl-pipeline"

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
