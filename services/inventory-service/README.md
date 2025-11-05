# Inventory Service - Endpoints

## 🌐 Endpoints

### 1. Health Check

```
GET /health
```

**Descripción:** Verifica que el servicio esté corriendo.

**Respuesta de ejemplo:**

```json
{
  "service": "inventory-service",
  "status": "healthy"
}
```

---

### 2. Obtener inventario

```
GET /inventory
```

**Descripción:** Devuelve el stock actual de todos los productos.

**Respuesta de ejemplo:**

```json
{
  "product-001": 50,
  "product-002": 20,
  "product-003": 10
}
```

---

### 3. Reducir stock (acción principal)

```
POST /update_stock
```

**Descripción:** Reduce en 1 unidad el stock de un producto. Puede fallar aleatoriamente para simular errores.

**Payload:**

```json
{
  "productId": "product-001"
}
```

**Respuesta de ejemplo (éxito):**

```json
{
  "inventory": {
    "productId": "product-001",
    "stockUpdated": true,
    "previousStock": 50,
    "currentStock": 49
  }
}
```

**Respuesta de ejemplo (error simulado):**

```json
{
  "detail": "Error aleatorio al actualizar stock"
}
```

---

### 4. Revertir stock (acción de compensación)

```
POST /revert_stock
```

**Descripción:** Restaura el stock de un producto previamente reducido.

**Payload:**

```json
{
  "productId": "product-001"
}
```

**Respuesta de ejemplo:**

```json
{
  "inventory": {
    "productId": "product-001",
    "reverted": true,
    "previousStock": 49,
    "currentStock": 50
  }
}
```
