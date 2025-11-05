from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import random
import uuid

app = FastAPI(
    title="Label Service",
    description="Servicio para generar y anular etiquetas de envío como parte de la SAGA."
)

# --- Variables de Entorno ---
SERVICE_NAME = os.getenv("SERVICE_NAME", "label-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 5004))
FAILURE_RATE = float(os.getenv("FAILURE_RATE", 0.2))

# --- "Base de Datos" de etiquetas generadas (en memoria) ---
# { "ORD-123": {"labelId": "LBL-ABCDEF", "status": "CREATED"} }
generated_labels_db = {}

def should_fail():
    return random.random() < FAILURE_RATE

@app.post("/generate_label")
async def generate_label(request: Request):
    """
    Creación de una nueva etiqueta.
    """
    saga_data = await request.json()
    order_id = saga_data.get("orderId")

    if not order_id:
        raise HTTPException(status_code=400, detail="Falta el campo 'orderId' en el objeto SAGA")

    if order_id in generated_labels_db:
        print(f"Etiqueta para Order ID '{order_id}' ya fue generada. Devolviendo éxito.")
        return JSONResponse({
            "label": generated_labels_db[order_id]
        }, status_code=200)

    if should_fail():
        print(f"Simulando fallo para Order ID '{order_id}' en Label Service.")
        raise HTTPException(status_code=503, detail="Error aleatorio simulado al generar la etiqueta")


    label_id = f"LBL-{uuid.uuid4().hex[:8].upper()}"
    
    new_label_data = {
        "labelId": label_id,
        "status": "CREATED"
    }
    generated_labels_db[order_id] = new_label_data
    
    print(f"Etiqueta '{label_id}' generada para Order ID '{order_id}'.")

    return JSONResponse({
        "label": new_label_data
    }, status_code=201)


@app.post("/void_label")
async def void_label(request: Request):
    """
    Anula una etiqueta previamente generada.
    """
    saga_data = await request.json()
    order_id = saga_data.get("orderId")

    if not order_id:
        raise HTTPException(status_code=400, detail="Falta el campo 'orderId' en el objeto SAGA")

    if order_id in generated_labels_db:
        removed_label = generated_labels_db.pop(order_id)
        print(f"Etiqueta '{removed_label['labelId']}' para Order ID '{order_id}' ha sido anulada.")
    else:
        print(f"No se encontró etiqueta para Order ID '{order_id}'. La compensación no es necesaria.")

    # Respuesta de compensación exitosa
    return JSONResponse({
        "label": {
            "orderId": order_id,
            "status": "COMPENSATED"
        }
    }, status_code=200)


@app.get("/labels")
async def get_all_labels():
    """Endpoint de utilidad para ver el estado actual de las etiquetas generadas."""
    return JSONResponse(generated_labels_db)


@app.get("/health")
async def health_check():
    """Health check para Kubernetes."""
    return JSONResponse({"service": SERVICE_NAME, "status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)