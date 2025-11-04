# Laboratorio: Patrón SAGA para Logística y Envío con Kubernetes

Este repositorio contiene la implementación de un flujo de logística y envío de productos utilizando una arquitectura de microservicios. El proyecto demuestra el **patrón de orquestación SAGA** para gestionar transacciones distribuidas, asegurando la atomicidad de la operación completa.

En caso de que un paso falle, el orquestador iniciará una serie de **transacciones de compensación** para revertir las acciones ya completadas, garantizando así la integridad de los datos y manteniendo un bajo acoplamiento entre servicios.

## Arquitectura de Microservicios

El flujo completo se compone de 10 microservicios coordinados por un **Orquestador**. Tu misión es elegir uno de los microservicios de la tabla, implementarlo y desplegarlo en Kubernetes.

| #      | Microservicio           | Puerto   | Falla Aleatoria | Acción Principal                                        | Compensación                                                |
| ------ | ----------------------- | -------- | --------------- | ------------------------------------------------------- | ----------------------------------------------------------- |
| **1**  | Orchestrator            | 5000     | No              | Coordina todas las operaciones                          | Coordina compensaciones                                     |
| **2**  | Warehouse Service       | 5001     | No              | Reserva espacio en almacén                              | Liberar espacio reservado                                   |
| **3**  | Inventory Service       | 5002     | ⚠️ 30%          | Descontar inventario                                    | Restock de productos                                        |
| **4**  | Package Service         | 5003     | No              | Empaquetar productos                                    | Deshacer empaquetado                                        |
| **5**  | Label Service           | 5004     | ⚠️ 20%          | Generar etiqueta de envío                               | Anular etiqueta                                             |
| **6**  | Carrier Service         | 5005     | No              | Asignar transportista                                   | Cancelar asignación                                         |
| **7**  | Pickup Service          | 5006     | No              | Programar recolección                                   | Cancelar recolección                                        |
| **8**  | Payment Service         | 5007     | ⚠️ 15%          | Procesar pago                                           | Reembolso/reversa de cargo                                  |
| **9**  | Notification Service    | 5008     | No              | Notificar confirmación al cliente                       | Notificar cancelación                                       |
| **10** | Tracking Service        | 5009     | No              | Actualizar estado a “EN TRÁNSITO”                       | Actualizar a “CANCELADO”                                    |
| **11** | Customer Service | 5010 | No              | Actualizar el historial del cliente (pedido completado) | Revertir estado del pedido (pedido cancelado) |

### Lógica de Compensación y Notificación

Si uno de los servicios propensos a fallar (Inventory, Label, Payment) devuelve un error, el Orquestador detendrá el flujo principal e iniciará la cadena de compensaciones.

Al final, ya sea por éxito o por fallo, los últimos tres servicios **siempre se ejecutarán** para registrar el estado final del pedido:
*   **En caso de éxito:** Notifican "pedido confirmado", marcan "EN TRÁNSITO", etc.
*   **En caso de fallo:** Notifican "pedido cancelado", marcan "CANCELADO", etc.

Al implementar estos tres servicios, ten en cuenta que su lógica de "compensación" es simplemente registrar el estado de cancelación, no necesariamente deshacer una acción previa.


## Flujo de la Transacción SAGA y Contratos de API

Para estandarizar la comunicación, el flujo sigue un patrón claro donde el Orquestador gestiona un objeto de estado central para cada pedido.

### 1. La Solicitud Inicial del Cliente

Todo comienza cuando un cliente envía una solicitud al **Orquestador** con la información básica del pedido. Por ejemplo, a un endpoint como `POST /orders`:

```json
{
  "user": "cliente-123",
  "product": "laptop-xyz",
  "quantity": 1,
  "shippingAddress": "Calle Falsa 123",
  "paymentDetails": "visa-ending-9876"
}
```
El **Orquestador** recibe esta solicitud, genera un `orderId` único y crea el objeto de estado SAGA.

### 2. El Objeto de Estado SAGA

Este objeto JSON actúa como un "pasaporte" que viaja a través del flujo. Contiene toda la información del pedido, los resultados de cada paso y el estado general de la transacción.

```json
{
  "orderId": "ORD-1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed",
  "status": "PENDING",
  "user": "cliente-123",
  "product": "laptop-xyz",
  "quantity": 1,
  "shippingAddress": "Calle Falsa 123",
  "paymentDetails": "visa-ending-9876",
  
  "generatedData": {
    "warehouse": null,
    "inventory": null,
    "package": null,
    "label": null,
    "carrier": null,
    "pickup": null,
    "payment": null,
    "notification": null,
    "tracking": null,
    "customer": null
  },
  
  "stepsCompleted": [],
  "compensationsExecuted": []
}
```
El Orquestador es responsable de:
1.  Llamar a cada microservicio en secuencia.
2.  Enviarles los datos que necesitan.
3.  Recibir sus respuestas y actualizar el campo `generatedData`.
4.  Registrar el paso completado en `stepsCompleted`.

### 3. Contrato de API para Cada Microservicio

A continuación se detalla lo que cada microservicio debe hacer y qué se espera que responda.

---
#### Warehouse Service
*   **Acción Principal (`POST /reserve`):** Reserva espacio físico para la orden.
*   **Respuesta esperada:**
    ```json
    { "warehouse": { "locationId": "BAY-A12", "spaceReserved": true } }
    ```
*   **Acción de Compensación (`POST /cancel_reservation`):** Libera el espacio previamente reservado.

---
#### Inventory Service
*   **Acción Principal (`POST /update_stock`):** Descuenta la cantidad del producto del inventario.
*   **Respuesta esperada:**
    ```json
    { "inventory": { "stockUpdated": true, "previousStock": 34, "currentStock": 33 } }
    ```
*   **Acción de Compensación (`POST /restock`):** Revierte el descuento, devolviendo los productos al stock.

---
#### Package Service
*   **Acción Principal (`POST /create_package`):** Genera una entrada para el paquete y lo asocia a la orden.
*   **Respuesta esperada:**
    ```json
    { "package": { "packageId": "PKG-4421", "status": "PACKAGED" } }
    ```
*   **Acción de Compensación (`POST /cancel_package`):** Marca el paquete como anulado.

---
#### Label Service
*   **Acción Principal (`POST /generate_label`):** Crea una etiqueta de envío con una guía.
*   **Respuesta esperada:**
    ```json
    { "label": { "labelId": "LBL-5542", "provider": "FastShip" } }
    ```
*   **Acción de Compensación (`POST /void_label`):** Anula la etiqueta generada.

---
#### Carrier Service
*   **Acción Principal (`POST /assign_carrier`):** Asigna el transportista más adecuado.
*   **Respuesta esperada:**
    ```json
    { "carrier": { "carrierId": "CRR-15-FastShip", "assigned": true } }
    ```
*   **Acción de Compensación (`POST /cancel_assignment`):** Libera al transportista de la asignación.

---
#### Pickup Service
*   **Acción Principal (`POST /schedule_pickup`):** Programa la fecha y hora de recolección.
*   **Respuesta esperada:**
    ```json
    { "pickup": { "pickupId": "PU-001", "scheduledAt": "2025-11-05T10:00:00Z" } }
    ```
*   **Acción de Compensación (`POST /cancel_pickup`):** Cancela la recolección programada.

---
#### Payment Service
*   **Acción Principal (`POST /process_payment`):** Procesa el cargo a los detalles de pago.
*   **Respuesta esperada:**
    ```json
    { "payment": { "transactionId": "TX-987123", "amount": 999.99, "status": "CONFIRMED" } }
    ```
*   **Acción de Compensación (`POST /refund_payment`):** Emite un reembolso o reversa el cargo.

---
#### Notification Service
*   **Acción Principal (`POST /send_confirmation`):** Notifica al cliente que su pedido fue procesado.
*   **Respuesta esperada:**
    ```json
    { "notification": { "confirmationSentTo": "cliente-123@email.com", "status": "SENT" } }
    ```
*   **Acción de Compensación (`POST /send_cancellation`):** Notifica al cliente la cancelación del pedido.

---
#### Tracking Service
*   **Acción Principal (`POST /start_tracking`):** Registra la orden en el sistema de seguimiento.
*   **Respuesta esperada:**
    ```json
    { "tracking": { "trackingId": "TRK-123456", "status": "IN_TRANSIT" } }
    ```
*   **Acción de Compensación (`POST /update_tracking_status`):** Actualiza el estado del seguimiento a "CANCELLED".

---
#### Customer Service
*   **Acción Principal (`POST /update_history`):** Actualiza el historial del cliente con el nuevo pedido.
*   **Respuesta esperada:**
    ```json
    { "customer": { "historyUpdated": true, "orderStatus": "COMPLETED" } }
    ```
*   **Acción de Compensación (`POST /update_history_cancellation`):** Actualiza el historial del pedido a "CANCELLED".

---

En caso de fallo, el JSON resultante tendria esta estructura:

```JSON
{
  "orderId": "ORD-1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed",
  "status": "FAILED_AND_COMPENSATED", // Un estado más descriptivo
  "user": "cliente-123",
  // ...otros datos...
  
  "generatedData": {
    "warehouse": { "locationId": "BAY-A12", "spaceReserved": true, "status": "COMPENSATED" },
    "inventory": { "stockUpdated": true, "previousStock": 34, "status": "COMPENSATED" },
    "package": { "packageId": "PKG-4421", "status": "COMPENSATED" },
    "label": { "labelId": "LBL-5542", "status": "COMPENSATED" },
    "carrier": { "carrierId": "CRR-15-FastShip", "status": "COMPENSATED" },
    "pickup": { "pickupId": "PU-001", "status": "COMPENSATED" },
    "payment": { "status": "FAILED", "error": "Insufficient funds" }, // Se registra el error
    
    // Los últimos 3 servicios se llaman con el contexto de cancelación
    "notification": { "cancellationSentTo": "cliente-123@email.com", "status": "SENT" },
    "tracking": { "trackingId": "TRK-123456", "status": "CANCELLED" },
    "customer": { "historyUpdated": true, "orderStatus": "CANCELLED" }
  },
  
  "stepsCompleted": ["warehouse", "inventory", "package", "label", "carrier", "pickup"],
  "compensationsExecuted": ["pickup", "carrier", "label", "package", "inventory", "warehouse"]
}
```

Las listas `stepsCompleted` y `compensationsExecuted` SOLO seran modificadas por el orquestador.

## Guía de Implementación

Cada microservicio puede ser desarrollado en el lenguaje que prefieras. Lo esencial es que siga estas directrices para integrarse correctamente en el clúster de Kubernetes.

#### 1. Endpoints Requeridos
Tu servicio debe exponer, como mínimo:
*   Un endpoint para la **acción principal** (ej. `POST /reserve`).
*   Un endpoint para la **acción de compensación** (ej. `POST /cancel_reservation`).
*   Un endpoint para revisar los elementos en la memoria del microservicio (ej. `POST /reservas`).
*   Un endpoint de `livenessProbe` para chequeo de salud (ej. `GET /health`) que devuelva un código `HTTP 200 OK`.

#### 2. Variables de Entorno
La aplicación debe ser configurable mediante variables de entorno, principalmente `SERVICE_NAME` y `SERVICE_PORT`. Esto permite que el mismo contenedor se comporte de manera diferente según cómo se despliegue.

#### 3. Empaquetado con Docker
Crea un `Dockerfile` para tu servicio. Este archivo se encargará de construir una imagen portable con todo lo necesario para ejecutar tu aplicación.

#### 4. Manifiestos de Kubernetes
Cada servicio requiere dos archivos YAML:
*   `deployment.yaml`: Define cómo Kubernetes debe ejecutar los contenedores de tu aplicación (réplicas, imagen, puertos, variables de entorno, etc.).
*   `service.yaml`: Crea un punto de acceso de red estable (un nombre DNS interno y una IP) para tus pods. Esto permite que el Orquestador se comunique con tu servicio sin necesidad de conocer la IP de cada pod.

A continuación, se presentan los manifiestos de `warehouse-service` como plantilla. **Recuerda adaptar los nombres, puertos e imagen a tu propio servicio.**

### Plantilla: `deployment.yaml`

```yaml
# services/warehouse-service/k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: warehouse-service # <-- CAMBIAR POR TU SERVICIO
  namespace: saga-shipping
  labels:
    app: warehouse-service # <-- CAMBIAR
spec:
  replicas: 1 # Puedes empezar con 1
  selector:
    matchLabels:
      app: warehouse-service # <-- CAMBIAR
  template:
    metadata:
      labels:
        app: warehouse-service # <-- CAMBIAR
    spec:
      containers:
      - name: warehouse-service-container # <-- CAMBIAR
        image: warehouse-service:latest # <-- CAMBIAR (usa tu imagen)
        imagePullPolicy: IfNotPresent # Ideal para desarrollo con Minikube
        ports:
        - containerPort: 5001 # <-- CAMBIAR
          name: http
        env:
        - name: SERVICE_NAME
          value: "warehouse-service" # <-- CAMBIAR
        - name: SERVICE_PORT
          value: "5001" # <-- CAMBIAR
        # Opcional: Para servicios que simulan fallos
        # - name: FAILURE_RATE
        #   value: "0.3" 
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /health # Endpoint de chequeo
            port: 5001 # <-- CAMBIAR
          initialDelaySeconds: 15
          periodSeconds: 20
```

### Plantilla: `service.yaml`

```yaml
# services/warehouse-service/k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: warehouse-service # <-- CAMBIAR
  namespace: saga-shipping
  labels:
    app: warehouse-service # <-- CAMBIAR
spec:
  type: ClusterIP # Solo accesible dentro del clúster
  selector:
    app: warehouse-service # <-- CAMBIAR
  ports:
  - name: http
    protocol: TCP
    port: 5001        # Puerto por el que el Service escucha
    targetPort: 5001  # Puerto del contenedor al que se redirige el tráfico
```

## Flujo de Trabajo y Comandos

Sigue estos pasos para desplegar tu microservicio en el clúster local de Minikube.

#### Paso 1: Levantar el Entorno Base
El `namespace` aísla nuestros servicios del resto del clúster. Aplícalo una sola vez.
```bash
kubectl apply -f k8s/namespace.yaml
```

#### Paso 2: Construir la Imagen Docker
Desde el directorio de tu servicio (donde está el `Dockerfile`), ejecuta:
```bash
# Ejemplo para warehouse-service
docker build -t warehouse-service:latest .
```

#### Paso 3: Cargar la Imagen en Minikube
Para que Minikube pueda usar la imagen que acabas de construir localmente sin necesidad de un registro externo, usa el siguiente comando:
```bash
# Ejemplo para warehouse-service
minikube image load warehouse-service:latest
```

#### Paso 4: Desplegar el Servicio en Kubernetes
Aplica tus archivos de manifiesto para crear el `Deployment` y el `Service`.
```bash
# Ejemplo para warehouse-service
kubectl apply -f services/warehouse-service/k8s/deployment.yaml
kubectl apply -f services/warehouse-service/k8s/service.yaml
```

## Comandos Útiles para Gestión

#### Listar Pods
Para ver si tus contenedores están corriendo correctamente.
```bash
kubectl get pods -n saga-shipping
```

#### Port-Forwarding (para pruebas)
Para acceder a tu servicio desde tu máquina local como si estuviera corriendo allí.
```bash
# Conecta tu puerto local 8080 al puerto 5001 del servicio warehouse-service
kubectl port-forward svc/warehouse-service 8080:5001 -n saga-shipping
```
Ahora puedes hacer peticiones a `http://localhost:8080`.

#### Reiniciar un Deployment
Útil si necesitas forzar que los pods se recreen con la imagen más reciente (si usas la tag `:latest`) o para recargar alguna configuración.
```bash
kubectl rollout restart deployment/warehouse-service -n saga-shipping
```

#### Eliminar el Entorno Completo
Para limpiar todos los recursos creados en este laboratorio.
```bash
kubectl delete namespace saga-shipping
```