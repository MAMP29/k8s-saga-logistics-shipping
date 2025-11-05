FROM python:3.11-slim


ENV SERVICE_NAME="pickup-service"
ENV SERVICE_PORT=5006


WORKDIR /app


COPY main.py /app


RUN pip install fastapi uvicorn


EXPOSE ${SERVICE_PORT}

# Comando de ejecución
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${SERVICE_PORT}"]