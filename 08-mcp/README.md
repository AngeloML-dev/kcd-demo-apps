# Paso 8 — MCP: Superpoderes para el Agente

Agregar Model Context Protocol (MCP) servers de Kubernetes y GitHub para que el agente pueda interactuar directamente con el cluster y el repositorio.

## Que es MCP

[MCP](https://modelcontextprotocol.io) es un protocolo abierto que conecta herramientas externas a un agente AI via un esquema estandarizado de "tools". En vez de hacer `subprocess.run(["kubectl", ...])` en Python, el agente llama a un MCP server que expone operaciones como tools invocables.

```
Sin MCP:  Ollama → Python → subprocess.run(["kubectl", ...])
Con MCP:  Ollama → Python → MCP Client → MCP Server (kubectl/GitHub)
```

MCP es independiente del LLM — es transporte, no inteligencia.

## Por que cambiar de modelo: modelo base vs qwen3.5:35b-a3b

En los pasos anteriores (01-07) usamos el modelo configurado en `.env` (por defecto `llama3.2`) para parsear lenguaje natural a JSON. Para eso un modelo pequeno es suficiente y rapido.

En este paso el agente necesita **function calling** (tool use): el LLM debe decidir que herramienta llamar, con que parametros, interpretar el resultado, y decidir el siguiente paso. Aqui es donde el modelo MoE brilla con su razonamiento multi-paso.

| Criterio | phi4-mini (3.8B) | qwen3.5:35b-a3b (MoE) |
|----------|-------------------|------------------------|
| Tarea | Parsear texto a JSON | Function calling + razonamiento |
| RAM | ~2 GB | ~18 GB |
| Velocidad (MLX) | 10-25 tok/s | ~68-134 tok/s |
| Function calling | Basico, inconsistente | Nativo, excelente |
| Razonamiento multi-paso | Limitado | Muy bueno |
| Hardware minimo | 8 GB RAM | 16 GB RAM + Apple Silicon |

### Cuando usar cada uno

- **phi4-mini / llama3.2** — Tareas de extraccion/clasificacion simples. Input → JSON. No necesita decidir que hacer, solo parsear. Ideal para Macs de 8 GB.
- **qwen3.5:35b-a3b** — Tareas agenticas donde el LLM debe elegir tools, interpretar resultados, manejar errores, y conversar sobre lo que hizo. Es el cerebro de un agente real. Gracias a MoE, solo activa 3.5B params por token = rapido incluso en 16 GB.

### Por que MoE y no un modelo denso grande?

Un modelo denso de 70B necesita ~40 GB de RAM y es lento. `qwen3.5:35b-a3b` ofrece function calling superior activando solo 3.5B parametros por token — calidad de modelo grande, velocidad de modelo pequeno.

## Que MCPs usamos

### 1. Kubernetes MCP

Reemplaza `core/kubernetes.py` (subprocess a kubectl). El agente puede:

- Listar pods, deployments, services
- Leer logs de un pod
- Describir recursos (eventos, condiciones)
- Verificar estado de health checks

**Uso en el flujo:** Paso 5 (esperar pods) + interaccion post-deploy.

### 2. GitHub MCP

Reemplaza `core/github.py` (requests a GitHub API). El agente puede:

- Leer PRs, diffs, checks
- Crear y mergear PRs
- Listar commits recientes
- Verificar estado de CI

**Uso en el flujo:** Paso 3 (verificar/mergear PR) + visibilidad del proceso.

## Como cambia el flujo

El pipeline principal no cambia — sigue siendo Ollama → Backstage → GitHub → ArgoCD → kubectl. Lo que cambia es:

```
Antes (pasos 01-07):
  [1] Ollama (modelo base)    → parsea intent
  [2] Backstage               → genera manifest + crea PR
  [3] Python requests          → mergea PR (hardcoded)
  [4] ArgoCD                   → sync
  [5] Python subprocess        → kubectl get pods (hardcoded)
      Fin. No hay mas interaccion.

Ahora (paso 08):
  [1] Ollama (qwen3.5:35b-a3b)→ parsea intent
  [2] Backstage                → genera manifest + crea PR
  [3] GitHub MCP               → verifica checks, mergea PR
  [4] ArgoCD                   → sync
  [5] Kubernetes MCP           → espera pods, lee logs, diagnostica
      |
      v
  El usuario puede seguir preguntando:
  "¿Por que tarda?"       → K8s MCP: lee eventos del pod
  "Muestrame los logs"    → K8s MCP: lee logs del container
  "¿Que PRs hay abiertos?"→ GitHub MCP: lista PRs
```

## Setup

```bash
# 1. Asegurate de tener Ollama 0.19+ (con MLX)
ollama --version

# 2. Descargar el modelo con function calling
make setup-model

# 3. Instalar dependencias Python (MCP SDK)
make install

# 4. Iniciar MCP servers
make start-mcp

# 5. Correr el agente con MCP
make run
```

## Requisitos de hardware

- Apple Silicon (M1/M2/M3/M4) — recomendado para maxima velocidad con MLX
- **32 GB RAM minimo recomendado**: el modelo ocupa ~18 GB y debe convivir con cluster y servicios.
- No ejecutar este paso en laptops Windows de 16 GB; usar el agente base con `llama3.2` (o `phi4-mini` como alternativa).
- 20 GB disco libre adicional (modelo + MCP servers)
- Ollama 0.19+ (usa MLX = ~134 tok/s en M4 Pro)

## Siguiente paso

Probar el agente con MCP en el flujo completo de la demo.
