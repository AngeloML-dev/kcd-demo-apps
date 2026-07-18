# KCD Peru 2026 — Workshop: Del YAML al lenguaje natural

**Construyendo una plataforma AI-native con Backstage y agentes en Kubernetes**

Un agente AI convierte una solicitud en lenguaje natural en pods corriendo en Kubernetes, pasando por Backstage (IDP), GitHub (GitOps) y ArgoCD — sin escribir YAML manualmente.

Antes de la sesión, completa la guía de [prerrequisitos](./PREREQUISITOS.md).

Todo corre 100% local en tu laptop. Usa **Ollama 0.19+** con backend **MLX** para inferencia ultra-rapida en Apple Silicon.

---

## Pasos del Workshop

| # | Carpeta | Que hace | Tiempo estimado |
|---|---------|----------|-----------------|
| 0 | [00-prerequisites](./00-prerequisites/) | Instalar herramientas base | 5 min |
| 1 | [01-ollama](./01-ollama/) | Configurar LLM local (Ollama 0.19+ MLX) | 5 min (+descarga) |
| 2 | [02-cluster](./02-cluster/) | Crear cluster Kubernetes local (kind) | 2 min |
| 3 | [03-argocd](./03-argocd/) | Instalar ArgoCD + conectar GitHub | 3 min |
| 4 | [04-backstage](./04-backstage/) | Instalar Backstage IDP (requerido) | 10 min |
| 5 | [05-agent](./05-agent/) | El agente AI (modo CLI) | 2 min |
| 6 | [06-web](./06-web/) | Portal web con animaciones SSE | 2 min |
| 7 | [07-demo](./07-demo/) | Correr el demo completo | 5 min |
| 8 | [08-mcp](./08-mcp/) | MCP servers (K8s + GitHub) + qwen3.5:35b-a3b | 10 min |

---

## Quick Start

```bash
# 1. Clonar y configurar
cp .env.example .env
# Editar .env: llenar GITHUB_TOKEN, GITHUB_REPO, y elegir modelo segun tu RAM

# 2. Setup automatico en macOS (todo de una vez)
make -f Makefile.macos setup-all

# 3. Correr el demo
make -f Makefile.macos demo  # modo CLI
make -f Makefile.macos web   # modo web (http://localhost:8888)
```

---

## Arquitectura

```
Usuario: "Despliega una API de usuarios con PostgreSQL en staging"
    |
    v
[1] Ollama (qwen3.5:35b-a3b)        ← parsea lenguaje natural a JSON (MLX backend)
    |
    v
[2] Backstage Scaffolder             ← genera YAML + crea PR en GitHub
    |
    v
[3] GitHub (auto-merge PR)           ← manifest en main
    |
    v
[4] ArgoCD                           ← detecta cambio, sincroniza cluster
    |
    v
[5] kind cluster                     ← pods corriendo
```

> **Backstage es el IDP.** El agente Python solo orquesta llamadas a APIs.
> No genera YAML ni pushea a GitHub — eso lo hace Backstage.

---

## Modelos por RAM disponible

| RAM | Modelo | Tipo | Velocidad (MLX) | Notas |
|-----|--------|------|-----------------|-------|
| **8 GB** | `llama3.2` | 3B denso | 10-25 tok/s | Modelo base: estable, ligero y con soporte para espanol |
| **8 GB** | `phi4-mini` | 3.8B denso | 10-25 tok/s | Alternativa opcional para razonamiento y matematicas |
| **16 GB Windows/WSL2** | `llama3.2` | 3B denso | Depende de CPU/GPU | Perfil estable con Docker, kind, ArgoCD y Backstage |
| **32 GB+** | `qwen3.5:35b-a3b` | 35B MoE (3.5B activos) | Depende de GPU | Demo completa y MCP |

Configura tu modelo en `.env` → variable `OLLAMA_MODEL`.

## Perfil Windows con 16 GB

El workshop soporta un perfil liviano para **WSL2 + Docker Desktop**. No uses PowerShell ni Git Bash para ejecutar los `Makefile` y scripts.

```bash
# Dentro de WSL2, desde la raiz del proyecto
make -f Makefile.windows setup
```

Este perfil usa `llama3.2`, un cluster kind de un nodo y Backstage como IDP requerido. MCP se omite en laptops de 16 GB. Deja **6–8 GB** asignados a Docker Desktop y descarga el modelo antes de la sesion. Para el flujo GitOps, completa `GITHUB_TOKEN` y `GITHUB_REPO` en `.env`, luego ejecuta `make -f Makefile.windows argocd-setup`.

---

## Comandos globales

```bash
make -f Makefile.macos setup-all # macOS: ejecuta pasos 00 al 03 en orden
make -f Makefile.windows setup   # Windows/WSL2: perfil liviano para 16 GB
make demo          # inicia agente CLI (paso 05)
make web           # inicia portal web (paso 06)
make status        # estado de pods en el cluster
make clean-apps    # elimina deployments generados
make clean-all     # elimina cluster completo
make help          # muestra todos los comandos
```

---

## Requisitos de hardware

- macOS con Apple Silicon (M1/M2/M3/M4) — recomendado para el demo completo
- Windows 11 con WSL2 + Docker Desktop — soportado con el perfil `setup-windows-16gb`
- **Ollama 0.19+** (backend MLX para maxima velocidad)
- 16 GB RAM: usar `llama3.2`; `phi4-mini` es opcional. 32 GB+ para `qwen3.5:35b-a3b` junto al stack completo
- 10-20 GB disco libre (modelo Ollama + imagenes Docker)
- Conexion a internet (para GitHub y descargas iniciales)

---

*KCD Peru 2026 — Platform Engineering + AI*
