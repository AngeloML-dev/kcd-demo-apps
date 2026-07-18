# Paso 5 — Agente AI (modo CLI)

El agente convierte lenguaje natural en pods corriendo en Kubernetes.

## Como funciona

El agente ejecuta 6 pasos en secuencia:

```
"Despliega una API de usuarios con PostgreSQL en staging con 3 replicas"
    |
    v
[1] Ollama       -> parsea intent (JSON)
[2] Backstage    -> ejecuta Software Template
[3] Manifests    -> genera YAML de Kubernetes
[4] GitHub       -> push al repo GitOps
[5] ArgoCD       -> fuerza sync inmediato
[6] kubectl      -> espera pods Running
```

Backstage es requerido: el agente usa su Software Template para generar los manifests y crear el Pull Request.

## Setup

```bash
# 1. Instalar dependencias Python
make install

# 2. Verificar que .env esta configurado
cat ../.env

# 3. Correr el agente
make run
```

## Ejemplos de solicitudes

```
Despliega una API de usuarios con PostgreSQL en staging con 3 replicas
Necesito un microservicio de pagos en produccion con 2 replicas
Crea un servicio de notificaciones en staging
Despliega una API de productos con base de datos MySQL
```

## Comandos dentro del agente

- `status` — muestra pods corriendo
- `salir` / `exit` / `q` — salir

## Servicios requeridos

Para ejecutar el flujo del workshop deben estar disponibles Ollama, Backstage, GitHub, ArgoCD y el clúster kind.

## Siguiente paso

Ir a [06-web](../06-web/) para el portal web con animaciones.

O ir directo a [07-demo](../07-demo/) para correr la demo completa.
