from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import random
from datetime import datetime

app = FastAPI(
    title="Pickup Service",
    description="Servicio para gestionar fecha y hora de entrega como parte de la SAGA."
)


SERVICE_NAME = os.getenv("SERVICE_NAME", "pickup-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5006"))


pickups_db  = {}


@app.post("/schedule_pickup")
async def reserve_space(request: Request):

    saga_data = await request.json()
    
    order_id = saga_data.get("orderId")
    request_data = saga_data.get("request_data", {})

    scheduled_at = request_data.get("scheduledAt")


    if not all([order_id, scheduled_at]):
        raise HTTPException(status_code=400, detail="Faltan campos requeridos: orderId o scheduledAt")


    if order_id in pickups_db :
        print(f"Pickup para Order ID '{order_id}' ya existe. Devolviendo éxito idempotente.")
        existing_pickup = pickups_db[order_id]
        return JSONResponse(content={"pickup": existing_pickup}, status_code=200)

    pickup_id = f"PU-{random.randint(100, 999)}"
    
    pickups_db[order_id] = {
        "pickupId": pickup_id,
        "scheduledAt": scheduled_at
    }
    print(f"Pickup programado para Order ID '{order_id}' con ID '{pickup_id}' a las {scheduled_at}.")


    response_content = {
            "pickup": {
                "pickupId": pickup_id,
                "scheduledAt": scheduled_at
            }
    }

    return JSONResponse(content=response_content, status_code=201)


@app.post("/cancel_pickup")
async def cancel_pickup(request: Request):
    saga_data = await request.json()
    order_id = saga_data.get("orderId")

    if not order_id:
        raise HTTPException(status_code=400, detail="Falta el campo 'orderId' en el objeto SAGA")

    if order_id in pickups_db:
        canceled_pickup = pickups_db.pop(order_id)
        print(f"Pickup '{canceled_pickup['pickupId']}' para Order ID '{order_id}' ha sido cancelado.")
        response_content = {
            "pickup": {
                "pickupId": canceled_pickup["pickupId"],
                "status": "CANCELLED"
            }
        }
        return JSONResponse(content=response_content, status_code=200)
    else:
        print(f"No se encontró pickup para Order ID '{order_id}'. Nada que cancelar.")
        response_content = {
            "pickup": {
                "orderId": order_id,
                "status": "NOT_FOUND_OR_ALREADY_CANCELLED"
            }
        }
        return JSONResponse(content=response_content, status_code=200)


@app.get("/pickups")
async def list_pickups():
    return JSONResponse({
        "current_pickups": pickups_db,
        "count": len(pickups_db)
    })


@app.get("/health")
async def health_check():
    return JSONResponse({"service": SERVICE_NAME, "status": "healthy"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)