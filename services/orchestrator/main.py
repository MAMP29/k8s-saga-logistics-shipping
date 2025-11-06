import os
import uuid
from typing import List, Dict, Any, Optional

import httpx
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Configuración de la Aplicación ---
app = FastAPI(
    title="SAGA Orchestrator",
    description="Orquesta el flujo de microservicios para procesar pedidos de logística."
)

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Lectura de URLs de Microservicios desde Variables de Entorno ---
URLS = {
    "warehouse": os.getenv("WAREHOUSE_URL", "http://localhost:5001"),
    "inventory": os.getenv("INVENTORY_URL", "http://localhost:5002"),
    "package": os.getenv("PACKAGE_URL", "http://localhost:5003"),
    "label": os.getenv("LABEL_URL", "http://localhost:5004"),
    "carrier": os.getenv("TRANSPORT_URL", "http://localhost:5005"),
    "pickup": os.getenv("PICKUP_URL", "http://localhost:5006"),
    "payment": os.getenv("PAYMENT_URL", "http://localhost:5007"),
    "notification": os.getenv("NOTIFICATION_URL", "http://localhost:5008"),
    "tracking": os.getenv("TRACKING_URL", "http://localhost:5009"),
    "customer": os.getenv("CUSTOMER_URL", "http://localhost:5010"),
}

# --- Definición de los Pasos de la SAGA ---
SAGA_STEPS = [
    {"name": "warehouse", "action": "/reserve_space", "compensation": "/cancel_reservation"},
    {"name": "inventory", "action": "/update_stock", "compensation": "/revert_stock"},
    {"name": "package", "action": "/create_package", "compensation": "/cancel_package"},
    {"name": "label", "action": "/generate_label", "compensation": "/void_label"},
    {"name": "carrier", "action": "/assign_carrier", "compensation": "/cancel_assignment"},
    {"name": "pickup", "action": "/schedule_pickup", "compensation": "/cancel_pickup"},
    #{"name": "payment", "action": "/process_payment", "compensation": "/refund_payment"},
]

# --- Modelos de Datos (Pydantic) ---
class OrderRequest(BaseModel):
    user: str
    product: str
    quantity: int
    shippingAddress: str
    paymentDetails: str

class GeneratedData(BaseModel):
    warehouse: Optional[Dict[str, Any]] = None
    inventory: Optional[Dict[str, Any]] = None
    package: Optional[Dict[str, Any]] = None
    label: Optional[Dict[str, Any]] = None
    carrier: Optional[Dict[str, Any]] = None
    pickup: Optional[Dict[str, Any]] = None
    payment: Optional[Dict[str, Any]] = None
    notification: Optional[Dict[str, Any]] = None
    tracking: Optional[Dict[str, Any]] = None
    customer: Optional[Dict[str, Any]] = None

class SagaState(BaseModel):
    orderId: str = Field(default_factory=lambda: f"ORD-{uuid.uuid4()}")
    status: str = "PENDING"
    request_data: OrderRequest
    generatedData: GeneratedData = Field(default_factory=GeneratedData)
    stepsCompleted: List[str] = []
    compensationsExecuted: List[str] = []

# --- "Base de Datos" en Memoria ---
sagas_db: Dict[str, SagaState] = {}

# --- Lógica del Orquestador ---

async def execute_saga(order_id: str):
    saga = sagas_db[order_id]
    saga.status = "PROCESSING"

    try:
        # --- Flujo Principal (Acciones) ---
        for step in SAGA_STEPS:
            step_name = step["name"]
            url = URLS[step_name] + step["action"]
            
            print(f"[SAGA {order_id}] ==> Executing step: {step_name} at {url}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=saga.dict())
                response.raise_for_status() # Lanza una excepción si el status no es 2xx
                
                # Actualizar el estado de la SAGA
                result = response.json()
                setattr(saga.generatedData, step_name, result.get(step_name))
                saga.stepsCompleted.append(step_name)
                sagas_db[order_id] = saga # Guardar progreso

        saga.status = "COMPLETED"
        print(f"[SAGA {order_id}] ==> Flow completed successfully. Executing final steps.")
        await execute_final_steps(saga, success=True)

    except httpx.HTTPStatusError as e:
        failed_step = step["name"]
        print(f"[SAGA {order_id}] ==> ❌ FAILED at step: {failed_step}. Reason: {e.response.text}")
        saga.status = "CANCELLING"
        
        # Guardar el error en el estado
        error_info = {"status": "FAILED", "error": e.response.text, "statusCode": e.response.status_code}
        setattr(saga.generatedData, failed_step, error_info)

        await execute_compensations(saga)
        await execute_final_steps(saga, success=False)

    finally:
        print(f"[SAGA {order_id}] ==> Final state: {saga.status}")
        sagas_db[order_id] = saga

async def execute_compensations(saga: SagaState):
    print(f"[SAGA {saga.orderId}] ==> Starting compensation flow...")
    steps_to_compensate = reversed(saga.stepsCompleted)
    
    for step_name in steps_to_compensate:
        step_info = next((s for s in SAGA_STEPS if s["name"] == step_name), None)
        if step_info:
            url = URLS[step_name] + step_info["compensation"]
            print(f"[SAGA {saga.orderId}] ==> Compensating step: {step_name} at {url}")
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(url, json=saga.dict())
                saga.compensationsExecuted.append(step_name)
            except Exception as comp_exc:
                print(f"[SAGA {saga.orderId}] ==> 🚨 CRITICAL: Compensation for {step_name} failed: {comp_exc}")
    
    saga.status = "FAILED_AND_COMPENSATED"

async def execute_final_steps(saga: SagaState, success: bool):
    """Llama a los servicios de notificación, seguimiento y cliente."""
    context = "confirmation" if success else "cancellation"
    
    await call_final_service("notification", f"/send_confirmation", saga)
    await call_final_service("tracking", f"/update_status", saga)
    await call_final_service("customer", f"/update_history", saga)

async def call_final_service(service_name: str, endpoint: str, saga: SagaState):
    try:
        url = URLS[service_name] + endpoint
        print(f"[SAGA {saga.orderId}] ==> Calling final service: {service_name}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=saga.dict())
            result = response.json()
            setattr(saga.generatedData, service_name, result.get(service_name))
    except Exception as e:
        print(f"[SAGA {saga.orderId}] ==> Warning: Final service {service_name} failed: {e}")

# --- Endpoints de la API ---

@app.post("/orders", status_code=202)
async def create_order(order_request: OrderRequest, background_tasks: BackgroundTasks):
    """
    Recibe un nuevo pedido, crea una SAGA y comienza la ejecución en segundo plano.
    """
    saga = SagaState(request_data=order_request)
    sagas_db[saga.orderId] = saga
    
    print(f"New SAGA created with Order ID: {saga.orderId}")
    background_tasks.add_task(execute_saga, saga.orderId)
    
    return {"message": "Order processing started.", "orderId": saga.orderId}

@app.get("/sagas/{order_id}")
async def get_saga_status(order_id: str):
    """
    Devuelve el estado actual de una SAGA específica.
    """
    if order_id not in sagas_db:
        raise HTTPException(status_code=404, detail="SAGA with that Order ID not found.")
    return sagas_db[order_id]

@app.get("/health")
async def health_check():
    return {"status": "healthy"}