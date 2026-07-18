# Core — Logica compartida

Este modulo contiene la logica de negocio compartida entre:

- **05-agent/** — Interfaz CLI interactiva (Rich)
- **06-web/** — Portal web con SSE (FastAPI)

Ambos importan desde `core` para evitar duplicacion. Si necesitas modificar el flujo de deployment (Ollama, Backstage, GitHub, ArgoCD), hazlo aqui y ambas interfaces se actualizan automaticamente.

## Estructura

| Archivo | Contenido |
|---|---|
| `config.py` | Carga de `.env` y configuracion |
| `checks.py` | Health checks (Ollama, Backstage, GitHub, ArgoCD, kubectl) |
| `intent.py` | Clasificacion y extraccion de intent via Ollama |
| `backstage.py` | Interaccion con Backstage Scaffolder |
| `github.py` | Creacion de PR y merge via GitHub API |
| `argocd.py` | Sincronizacion con ArgoCD |
| `kubernetes.py` | Operaciones con kubectl (pods, deployments) |
| `helpers.py` | Headers HTTP y utilidades comunes |
