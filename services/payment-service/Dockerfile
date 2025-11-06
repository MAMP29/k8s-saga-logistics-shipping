FROM python:3.11-slim


ENV SERVICE_NAME="payment-service"
ENV SERVICE_PORT=5007
ENV FAILURE_RATE=0.15

WORKDIR /app


COPY main.py /app


RUN pip install fastapi uvicorn


EXPOSE ${SERVICE_PORT}

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${SERVICE_PORT}"]