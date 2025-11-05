from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os

app = FastAPI(
    title="Customer Service",
    description="Servicio para gestionar el historial de clientes como parte de la SAGA."
)

# --- Variables de Entorno ---
SERVICE_NAME = os.getenv("SERVICE_NAME", "customer-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5010"))

# --- Almacenamiento en Memoria (Base de datos simulada) ---
# { "orderId-123": {"user": "...", "product": "...", "orderStatus": "COMPLETED"} }
customer_history_db = {}


@app.post("/update_history")
async def update_history(request: Request):
    """
    Acción Principal: Actualiza el historial del cliente con el nuevo pedido.
    Es idempotente: si el historial para esta orden ya existe, devuelve el éxito.
    """
    saga_data = await request.json()
    order_id = saga_data.get("orderId")
    user = saga_data.get("user")
    product = saga_data.get("product")

    if not all([order_id, user, product]):
        raise HTTPException(status_code=400, detail="Faltan campos requeridos en el objeto SAGA: orderId, user, product")

    # --- Lógica de Idempotencia ---
    if order_id in customer_history_db:
        print(f"Historial para Order ID '{order_id}' ya existe. Devolviendo éxito.")
        response_content = {
            "customer": {
                "historyUpdated": True,
                "orderStatus": "COMPLETED"
            }
        }
        return JSONResponse(content=response_content, status_code=200)

    # --- Lógica de Negocio ---
    # Simula la actualización del historial del cliente
    customer_history_db[order_id] = {
        "user": user,
        "product": product,
        "orderStatus": "COMPLETED"
    }
    print(f"Historial actualizado para Order ID '{order_id}' - Usuario: '{user}', Producto: '{product}'.")

    # --- Construcción de la Respuesta según el Contrato SAGA ---
    response_content = {
        "customer": {
            "historyUpdated": True,
            "orderStatus": "COMPLETED"
        }
    }
    return JSONResponse(content=response_content, status_code=201) # 201 Created es más apropiado aquí


@app.post("/update_history_cancellation")
async def update_history_cancellation(request: Request):
    """
    Acción de Compensación: Actualiza el historial del pedido a "CANCELLED".
    """
    saga_data = await request.json()
    order_id = saga_data.get("orderId")

    if not order_id:
        raise HTTPException(status_code=400, detail="Falta el campo 'orderId' en el objeto SAGA")

    if order_id in customer_history_db:
        # Actualiza el estado a CANCELLED en lugar de eliminar
        customer_history_db[order_id]["orderStatus"] = "CANCELLED"
        print(f"Historial para Order ID '{order_id}' actualizado a CANCELLED.")
        
        # Respuesta de compensación exitosa
        response_content = {
            "customer": {
                "orderId": order_id,
                "status": "COMPENSATED"
            }
        }
        return JSONResponse(content=response_content, status_code=200)
    else:
        # Si el historial no existe, la compensación se considera exitosa (ya no está).
        print(f"No se encontró historial para Order ID '{order_id}'. La compensación no es necesaria.")
        response_content = {
            "customer": {
                "orderId": order_id,
                "status": "NOT_FOUND_OR_ALREADY_COMPENSATED"
            }
        }
        return JSONResponse(content=response_content, status_code=200)


@app.get("/history")
async def list_history():
    """Endpoint de utilidad para ver el estado actual del historial de clientes."""
    return JSONResponse({
        "customer_history": customer_history_db,
        "count": len(customer_history_db)
    })


@app.get("/health")
async def health_check():
    """Verifica el estado del servicio para Kubernetes."""
    return JSONResponse({"service": SERVICE_NAME, "status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)