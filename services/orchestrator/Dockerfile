FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# El puerto 5000 es el que definiste en el deployment
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]