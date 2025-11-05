FROM python:3.11-slim

# Variables de entorno por defecto (pueden sobreescribirse en el deployment)
ENV SERVICE_NAME="customer-service"
ENV SERVICE_PORT=5010

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos
COPY main.py /app

# Instalar dependencias
RUN pip install fastapi uvicorn

# Exponer el puerto configurado
EXPOSE ${SERVICE_PORT}

# Comando de ejecución
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${SERVICE_PORT}"]