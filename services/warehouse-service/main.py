from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import random # Para generar un ID de ubicación de ejemplo

app = FastAPI(
    title="Warehouse Service",
    description="Servicio para gestionar reservas de espacio en el almacén como parte de la SAGA."
)

# --- Variables de Entorno ---
SERVICE_NAME = os.getenv("SERVICE_NAME", "warehouse-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5001"))

# --- Almacenamiento en Memoria (Base de datos simulada) ---
# { "orderId-123": {"user": "...", "product": "...", "locationId": "..."} }
reservations_db = {}


@app.post("/reserve_space")
async def reserve_space(request: Request):
    """
    Acción Principal: Reserva espacio en el almacén para una orden.
    Es idempotente: si la reserva para esta orden ya existe, devuelve el éxito.
    """
    saga_data = await request.json()
    
    order_id = saga_data.get("orderId")
    request_data = saga_data.get("request_data", {})
    
    user = request_data.get("user")
    product = request_data.get("product")

    if not all([order_id, user, product]):
        raise HTTPException(status_code=400, detail="Faltan campos requeridos en el objeto SAGA: orderId, user, product")

    # --- Lógica de Idempotencia ---
    if order_id in reservations_db:
        print(f"Reserva para Order ID '{order_id}' ya existe. Devolviendo éxito.")
        location_id = reservations_db[order_id]["locationId"]
        response_content = {
            "warehouse": {
                "locationId": location_id,
                "spaceReserved": True
            }
        }
        return JSONResponse(content=response_content, status_code=200)

    # --- Lógica de Negocio ---
    # Simula la asignación de un espacio físico en el almacén
    location_id = f"BAY-{random.randint(10, 99)}"
    
    reservations_db[order_id] = {
        "user": user,
        "product": product,
        "locationId": location_id
    }
    print(f"Espacio reservado para Order ID '{order_id}' en la ubicación '{location_id}'.")

    # --- Construcción de la Respuesta según el Contrato SAGA ---
    response_content = {
        "warehouse": {
            "locationId": location_id,
            "spaceReserved": True
        }
    }
    return JSONResponse(content=response_content, status_code=201) # 201 Created es más apropiado aquí


@app.post("/cancel_reservation")
async def cancel_reservation(request: Request):
    """
    Acción de Compensación: Libera un espacio previamente reservado.
    """
    saga_data = await request.json()
    
    order_id = saga_data.get("orderId")
    request_data = saga_data.get("request_data", {})
    
    user = request_data.get("user")
    product = request_data.get("product")

    if not order_id:
        raise HTTPException(status_code=400, detail="Falta el campo 'orderId' en el objeto SAGA")

    if order_id in reservations_db:
        removed_reservation = reservations_db.pop(order_id)
        print(f"Reserva para Order ID '{order_id}' en '{removed_reservation['locationId']}' ha sido cancelada.")
        
        # Respuesta de compensación exitosa
        response_content = {
            "warehouse": {
                "orderId": order_id,
                "status": "COMPENSATED"
            }
        }
        return JSONResponse(content=response_content, status_code=200)
    else:
        # Si la reserva no existe, la compensación se considera exitosa (ya no está).
        print(f"No se encontró reserva para Order ID '{order_id}'. La compensación no es necesaria.")
        response_content = {
            "warehouse": {
                "orderId": order_id,
                "status": "NOT_FOUND_OR_ALREADY_COMPENSATED"
            }
        }
        return JSONResponse(content=response_content, status_code=200)


@app.get("/reservations")
async def list_reservations():
    """Endpoint de utilidad para ver el estado actual de las reservas."""
    return JSONResponse({
        "current_reservations": reservations_db,
        "count": len(reservations_db)
    })


@app.get("/health")
async def health_check():
    """Verifica el estado del servicio para Kubernetes."""
    return JSONResponse({"service": SERVICE_NAME, "status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)