#!/usr/bin/env bash

# --- deploy.sh ---
# Script para construir y desplegar todos los microservicios en Minikube.

# Detiene el script inmediatamente si cualquier comando falla (principio de atomicidad).
set -e

# --- Colores para la salida ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sin color

echo -e "${YELLOW}Iniciando el despliegue de la arquitectura SAGA...${NC}"

# --- Paso 1: Verificar que Minikube esté corriendo ---
if ! minikube status &> /dev/null; then
    echo "❌ Error: Minikube no está corriendo. Por favor, inicia Minikube con 'minikube start'."
    exit 1
fi

# --- Paso 2: Conectar la terminal al entorno de Docker de Minikube ---
# Esto es crucial. Construye las imágenes DIRECTAMENTE dentro de Minikube,
# eliminando la necesidad del lento comando 'minikube image load'.
echo -e "${YELLOW}Configurando el entorno de Docker para que apunte a Minikube...${NC}"
eval $(minikube -p minikube docker-env)
echo -e "${GREEN}Entorno de Docker configurado.${NC}"

# --- Paso 3: Aplicar el Namespace ---
echo -e "${YELLOW}Aplicando el namespace 'saga-shipping'...${NC}"
kubectl apply -f k8s/namespace.yaml
echo -e "${GREEN}Namespace aplicado.${NC}"

# --- Paso 4: Bucle para construir y desplegar cada servicio ---
for service_dir in services/*/; do
    # Extraer el nombre del servicio del nombre del directorio
    service_name=$(basename "$service_dir")
    
    echo -e "\n${YELLOW}--- Procesando servicio: $service_name ---${NC}"

    # Construir la imagen de Docker si existe un Dockerfile
    if [ -f "${service_dir}Dockerfile" ]; then
        echo "Construyendo la imagen de Docker para $service_name..."
        docker build -t "$service_name:latest" "$service_dir"
        echo -e "${GREEN}Imagen '$service_name:latest' construida exitosamente.${NC}"
    else
        echo "No se encontró Dockerfile para $service_name. Saltando la construcción de la imagen."
    fi

    # Desplegar los manifiestos de Kubernetes si existe la carpeta k8s
    if [ -d "${service_dir}k8s" ]; then
        echo "Desplegando manifiestos de Kubernetes para $service_name..."
        # El comando apply puede tomar un directorio entero
        kubectl apply -f "${service_dir}k8s/"
        echo -e "${GREEN}Manifiestos para $service_name desplegados exitosamente.${NC}"
    else
        echo "No se encontró el directorio k8s para $service_name. Saltando el despliegue."
    fi
done

echo -e "\n${GREEN}✅ ¡Despliegue completado!${NC}"
echo -e "Espera unos momentos para que todos los pods se inicien."
echo -e "Para verificar el estado de los pods, ejecuta: ${YELLOW}kubectl get pods -n saga-shipping${NC}"
echo -e "Para acceder al Orchestrator, busca el puerto con: ${YELLOW}minikube service orchestrator -n saga-shipping --url${NC}"