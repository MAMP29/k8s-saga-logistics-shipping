from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import datetime

app = FastAPI(
    title="Notification Service",
    description="Servicio encargado de enviar confirmaciones y cancelaciones dentro de la SAGA de logística."
)

# ---- Variables de entorno ---
SERVICE_NAME = os.getenv("SERVICE_NAME", "notification-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5008"))

# ---- Base de datos simulada (en memoria) ---
notifications_db = []


@app.post("/send_confirmation")
async def send_confirmation(request: Request):
    """Envía una notificación de confirmación de pedido."""
    saga_data = await request.json()
    order_id = saga_data.get("orderId")
    user = saga_data.get("user")

    if not all([order_id, user]):
        raise HTTPException(status_code=400, detail="Faltan campos requeridos: orderId y user")

    notification = {
        "orderId": order_id,
        "type": "CONFIRMATION",
        "user": user,
        "timestamp": datetime.datetime.now().isoformat()
    }
    notifications_db.append(notification)
    print(f"✅ Notificación de CONFIRMACIÓN enviada para Order ID '{order_id}'")

    return JSONResponse(
        {"notification": notification, "status": "SENT"},
        status_code=201
    )


@app.post("/send_cancellation")
async def send_cancellation(request: Request):
    """Envía una notificación de cancelación (compensación)."""
    saga_data = await request.json()
    order_id = saga_data.get("orderId")
    user = saga_data.get("user")

    if not all([order_id, user]):
        raise HTTPException(status_code=400, detail="Faltan campos requeridos: orderId y user")

    notification = {
        "orderId": order_id,
        "type": "CANCELLATION",
        "user": user,
        "timestamp": datetime.datetime.now().isoformat()
    }
    notifications_db.append(notification)
    print(f"⚠️ Notificación de CANCELACIÓN enviada para Order ID '{order_id}'")

    return JSONResponse(
        {"notification": notification, "status": "SENT"},
        status_code=200
    )


@app.get("/notifications")
async def list_notifications():
    """Devuelve todas las notificaciones enviadas (para depuración o monitoreo)."""
    return JSONResponse({"count": len(notifications_db), "notifications": notifications_db})


@app.get("/health")
async def health_check():
    """Verifica la salud del servicio."""
    return JSONResponse({"service": SERVICE_NAME, "status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
