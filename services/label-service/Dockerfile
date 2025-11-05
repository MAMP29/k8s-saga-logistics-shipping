FROM python:3.11-slim

# Variables de entorno por defecto
ENV SERVICE_NAME="label-service"
ENV SERVICE_PORT=5004
ENV FAILURE_RATE=0.4

WORKDIR /app

RUN pip install fastapi uvicorn

COPY main.py /app

EXPOSE ${SERVICE_PORT}

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${SERVICE_PORT}"]