from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import random

app = FastAPI(
    title="Inventory Service",
    description="Servicio para gestionar inventario como parte de la SAGA."
)

# --- Variables de Entorno ---
SERVICE_NAME = os.getenv("SERVICE_NAME", "inventory-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 5002))
FAILURE_RATE = float(os.getenv("FAILURE_RATE", 0.3))  # 30% de fallos

# --- Inventario simulado (en memoria) ---
# { "product-123": stock }
inventory_db = {"product-001": 50, "product-002": 20, "product-003": 10}

def should_fail():
    return random.random() < FAILURE_RATE

@app.post("/update_stock")
async def update_stock(request: Request):
    """
    Acción principal: reducir stock de un producto.
    Falla aleatoriamente según FAILURE_RATE para simular errores.
    """

    saga_data = await request.json()

    data = await request.json()
    request_data = saga_data.get("request_data", {})
    product = request_data.get("product")

    if not product:
        raise HTTPException(status_code=400, detail="Falta 'product' en la SAGA")

    if product not in inventory_db:
        raise HTTPException(status_code=404, detail=f"Producto {product} no encontrado")

    if should_fail():
        raise HTTPException(status_code=500, detail="Error aleatorio al actualizar stock")

    previous_stock = inventory_db[product]
    inventory_db[product] -= 1

    return JSONResponse({
        "inventory": {
            "product": product,
            "stockUpdated": True,
            "previousStock": previous_stock,
            "currentStock": inventory_db[product]
        }
    }, status_code=200)

@app.post("/revert_stock")
async def revert_stock(request: Request):
    """
    Acción de compensación: restaurar stock de un producto.
    """

    saga_data = await request.json()
    
    request_data = saga_data.get("request_data", {})
    product = request_data.get("product")

    if not product:
        raise HTTPException(status_code=400, detail="Falta 'product' en la SAGA")

    if product not in inventory_db:
        inventory_db[product] = 1  # inicializa si no existía

    previous_stock = inventory_db[product]
    inventory_db[product] += 1

    return JSONResponse({
        "inventory": {
            "product": product,
            "reverted": True,
            "previousStock": previous_stock,
            "currentStock": inventory_db[product]
        }
    }, status_code=200)

@app.get("/inventory")
async def get_inventory():
    """Endpoint de utilidad para ver el stock actual."""
    return JSONResponse(inventory_db)

@app.get("/health")
async def health():
    """Health check para Kubernetes."""
    return JSONResponse({"service": SERVICE_NAME, "status": "healthy"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)