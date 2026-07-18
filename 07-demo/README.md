# Paso 7 — Correr el Demo

Guion completo para la demo en el KCD Peru 2026.

## Pre-requisitos

Todos los pasos anteriores (00-06) deben estar completados, o al minimo:
- Ollama 0.19+ corriendo con el modelo configurado en `.env` (`01-ollama`)
- Cluster kind activo (`02-cluster`)
- `.env` configurado

## Sesion de demo — 4 terminales

Abrir 4 terminales antes de empezar:

| Terminal | Comando | URL |
|----------|---------|-----|
| 1 — LLM | `ollama serve` | — |
| 2 — IDP | `cd ../04-backstage && make start` | http://localhost:3000 |
| 3 — Portal | `cd ../06-web && make run` | http://localhost:8888 |
| 4 — GitOps | `cd ../03-argocd && make ui` | https://localhost:8080 |

O usar el comando automatico:

```bash
make start-all
```

## Guion en el escenario

1. **Mostrar el portal** — http://localhost:8888 en pantalla completa
2. **Escribir solicitud:**
   ```
   Despliega una API de usuarios con PostgreSQL en staging con 3 replicas
   ```
3. **Narrar cada paso** mientras las animaciones avanzan:
   - "Ollama parsea la intencion con un LLM local..."
   - "Backstage ejecuta el Software Template..."
   - "Se genera el manifest YAML..."
   - "Se hace push a GitHub..."
   - "ArgoCD detecta el cambio..."
   - "Los pods ya estan corriendo!"
4. **Cambiar a Backstage** — http://localhost:3000 -> nuevo componente en el catalogo
5. **Cambiar a ArgoCD** — https://localhost:8080 -> estado Synced
6. **Terminal:** `kubectl get pods -n staging`
7. **Opcional:** Abrir GitHub y mostrar el commit del agente

## Ejemplos de solicitudes

```
Despliega una API de usuarios con PostgreSQL en staging con 3 replicas
Necesito un microservicio de pagos en produccion con 2 replicas
Crea un servicio de notificaciones en staging
Despliega una API de productos con base de datos MySQL
```

## Verificar estado

```bash
make check
```

## Limpiar despues del demo

```bash
make clean-apps    # solo los deployments
make clean-all     # todo (cluster incluido)
```
