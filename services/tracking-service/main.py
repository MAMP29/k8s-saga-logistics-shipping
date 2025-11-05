from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import uuid

app = FastAPI(
    title="Tracking Service",
    description="Servicio para gestionar el estado de seguimiento de pedidos como parte de la SAGA."
)

# --- Variables de Entorno ---
SERVICE_NAME = os.getenv("SERVICE_NAME", "tracking-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 5009))

# --- "Base de Datos" de seguimiento (en memoria) ---
# Usamos un diccionario con orderId como clave para idempotencia.
# { "ORD-123": {"trackingId": "TRK-ABCDEF", "status": "IN_TRANSIT"} }
tracking_db = {}

@app.post("/update_status")
async def update_tracking_status(request: Request):
    """
    Acción de Finalización: Crea o actualiza el registro de seguimiento
    basándose en el estado final de la SAGA.
    """
    saga_data = await request.json()
    order_id = saga_data.get("orderId")
    saga_status = saga_data.get("status")

    if not order_id or not saga_status:
        raise HTTPException(status_code=400, detail="Faltan 'orderId' o 'status' en el objeto SAGA")

    # --- Lógica de Negocio: Determinar el estado final ---
    final_tracking_status = ""
    if saga_status == "COMPLETED":
        final_tracking_status = "IN_TRANSIT"
    elif saga_status == "FAILED_AND_COMPENSATED":
        final_tracking_status = "CANCELLED"
    else:
        # No debería ocurrir, pero es una buena práctica manejarlo
        final_tracking_status = "UNKNOWN"

    # --- Lógica de Idempotencia y Creación/Actualización ---
    if order_id in tracking_db:
        # Si ya existe, solo actualizamos el estado
        tracking_db[order_id]["status"] = final_tracking_status
        print(f"Estado de seguimiento para Order ID '{order_id}' actualizado a '{final_tracking_status}'.")
    else:
        # Si no existe, creamos un nuevo registro
        tracking_id = f"TRK-{uuid.uuid4().hex[:10].upper()}"
        tracking_db[order_id] = {
            "trackingId": tracking_id,
            "status": final_tracking_status
        }
        print(f"Registro de seguimiento '{tracking_id}' creado para Order ID '{order_id}' con estado '{final_tracking_status}'.")

    # --- Respuesta según el Contrato SAGA ---
    return JSONResponse({
        "tracking": tracking_db[order_id]
    }, status_code=200)


@app.get("/trackings")
async def get_all_trackings():
    """Endpoint de utilidad para ver todos los registros de seguimiento."""
    return JSONResponse(tracking_db)


@app.get("/health")
async def health_check():
    """Health check para Kubernetes."""
    return JSONResponse({"service": SERVICE_NAME, "status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)