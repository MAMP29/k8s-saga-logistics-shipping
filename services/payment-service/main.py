from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import random 

app = FastAPI(
    title="Payment Service",
    description="Servicio para procesar pagos como parte de la SAGA."
)


SERVICE_NAME = os.getenv("SERVICE_NAME", "payment-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5007"))
FAILURE_RATE = float(os.getenv("FAILURE_RATE", 0.15))


payments_db = {}

@app.post("/process_payment")
async def process_payment(request: Request):


    """
    Acción principal: procesa un pago y devuelve un transactionId.
    """
    saga_data = await request.json()

    order_id = saga_data.get("orderId")
    request_data = saga_data.get("request_data", {})

    amount = request_data.get("amount")



    if not all([order_id, amount]):
        raise HTTPException(status_code=400, detail="Faltan campos requeridos: orderId o amount")
    
    if random.random() < FAILURE_RATE:
        print(f"Pago para Order ID '{order_id}' FALLÓ intencionalmente (simulación).")
        return JSONResponse(
            content={"payment": {"orderId": order_id, "status": "FAILED", "error": "Simulated failure"}},
            status_code=500
        )

    # Idempotencia: si ya se procesó, devolver la misma respuesta
    if order_id in payments_db:
        print(f"Pago para Order ID '{order_id}' ya fue procesado. Devolviendo éxito idempotente.")
        existing_payment = payments_db[order_id]
        return JSONResponse(content={"payment": existing_payment}, status_code=200)

    # Simulación de lógica de negocio (procesar pago)
    transaction_id = f"TX-{random.randint(100000, 999999)}"
    processed_payment = {
        "transactionId": transaction_id,
        "amount": amount,
        "status": "CONFIRMED"
    }

    payments_db[order_id] = processed_payment

    print(f"Pago procesado para Order ID '{order_id}' con Transacción '{transaction_id}' por ${amount}.")

    return JSONResponse(content={"payment": processed_payment}, status_code=201)



@app.post("/refund_payment")
async def refund_payment(request: Request):
    """
    Acción de compensación: reembolsa un pago previamente procesado.
    """
    saga_data = await request.json()
    order_id = saga_data.get("orderId")

    if not order_id:
        raise HTTPException(status_code=400, detail="Falta el campo 'orderId' en el objeto SAGA")

    if order_id in payments_db:
        refunded_payment = payments_db.pop(order_id)
        print(f"Pago '{refunded_payment['transactionId']}' para Order ID '{order_id}' ha sido reembolsado.")
        response_content = {
            "payment": {
                "transactionId": refunded_payment["transactionId"],
                "status": "REFUNDED"
            }
        }
        return JSONResponse(content=response_content, status_code=200)
    else:
        print(f"No se encontró pago para Order ID '{order_id}'. Nada que reembolsar.")
        response_content = {
            "payment": {
                "orderId": order_id,
                "status": "NOT_FOUND_OR_ALREADY_REFUNDED"
            }
        }
        return JSONResponse(content=response_content, status_code=200)


@app.get("/payments")
async def list_payments():
    """Endpoint auxiliar para ver pagos procesados."""
    return JSONResponse({
        "current_payments": payments_db,
        "count": len(payments_db)
    })


@app.get("/health")
async def health_check():
    """Health check para Kubernetes."""
    return JSONResponse({"service": SERVICE_NAME, "status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)