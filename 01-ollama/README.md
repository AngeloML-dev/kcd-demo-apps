# Paso 1 — Ollama (LLM local)

Configurar el modelo de lenguaje que parsea solicitudes en lenguaje natural a JSON estructurado.

## Que es Ollama

[Ollama](https://ollama.com) permite correr LLMs localmente. Desde la version **0.19+**, usa **MLX** como backend en Apple Silicon — esto duplica la velocidad de inferencia respecto a versiones anteriores (llama.cpp).

En Linux/Windows usa CUDA (NVIDIA) o CPU.

## Modelos recomendados por RAM

| RAM | Modelo | Params activos | Tamano | Velocidad (Apple Silicon) | Notas |
|-----|--------|---------------|--------|---------------------------|-------|
| **8 GB** | `llama3.2` | 3B | ~2 GB | 10-25 tok/s | Modelo base: ligero, soporte para espanol y tool use |
| **8 GB** | `phi4-mini` | 3.8B | ~2.5 GB | 10-25 tok/s | Alternativa opcional para razonamiento y matematicas |
| **16 GB Windows/WSL2** | `llama3.2` | 3B | ~2 GB | Depende de CPU/GPU | Recomendado junto con Docker, kind, ArgoCD y Backstage |
| **32 GB+** | `qwen3.5:35b-a3b` | 3.5B (MoE) | ~18 GB | Depende de GPU | Demo completa y MCP |

> **MoE (Mixture of Experts):** `qwen3.5:35b-a3b` tiene 35B parametros totales pero solo activa 3.5B por token. Esto le da la calidad de un modelo grande con la velocidad de uno pequeno.

El modelo base del workshop es **`llama3.2`** para que el demo funcione en equipos de 16 GB. `phi4-mini` es una alternativa opcional si se quiere priorizar razonamiento y matematicas. Usa `qwen3.5:35b-a3b` solo en equipos de 32 GB o más, y no junto con Backstage/MCP en una laptop de 16 GB.

## Setup

```bash
# 1. Asegurate de tener Ollama 0.19+ (con MLX)
ollama --version    # debe ser >= 0.19
brew upgrade ollama # actualizar si es necesario

# 2. Descargar el modelo (~18 GB para qwen3.5, ~2 GB para phi4-mini)
make setup

# 3. Iniciar el servidor (en una terminal separada)
make start

# 4. Probar que funciona
make test
```

## Como funciona en el demo

El agente envia un prompt al endpoint `/api/generate` de Ollama:

```
Usuario: "Despliega una API de usuarios con PostgreSQL en staging con 3 replicas"
                                    |
                                    v
                        Ollama (qwen3.5:35b-a3b)
                                    |
                                    v
{
  "service_name": "api-usuarios",
  "environment": "staging",
  "replicas": 3,
  "port": 8080,
  "has_database": true,
  "db_type": "postgresql",
  "owner": "backend-team"
}
```

## Probar manualmente

```bash
# Pregunta directa
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3.5:35b-a3b",
  "prompt": "What is Kubernetes in one sentence?",
  "stream": false
}' | python3 -m json.tool
```

## Por que Ollama 0.19+ con MLX

Desde marzo 2026, Ollama usa **MLX** como motor de inferencia en Apple Silicon:

- **57% mas rapido en prefill** (procesar el prompt)
- **93% mas rapido en decode** (generar tokens)
- Mejor manejo de la memoria unificada de Apple Silicon
- Mismo API, mismo CLI — zero cambios de codigo

Antes de 0.19, Ollama usaba llama.cpp que no aprovechaba la arquitectura de Apple Silicon. Ahora no hay razon para usar backends alternativos.

## Instalacion por plataforma

### macOS

```bash
brew install ollama
# O si ya lo tienes instalado:
brew upgrade ollama
```

Usa **MLX (GPU Apple Silicon)** para inferencia rapida. En M4 Pro, `qwen3.5:35b-a3b` genera ~134 tok/s.

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

- Con **GPU NVIDIA**: instalar [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). Ollama detecta CUDA automaticamente.
- **Sin GPU**: funciona con CPU, pero las respuestas seran mas lentas. Usar `phi4-mini` o `llama3.2` para mejor experiencia.

### Windows

Descargar el instalador desde [ollama.com/download/windows](https://ollama.com/download/windows).

- Con **GPU NVIDIA**: requiere drivers actualizados con soporte CUDA.
- Con **WSL2**: instalar Ollama dentro de WSL2 siguiendo las instrucciones de Linux.
- Para 16 GB: ejecutar `make -f Makefile.windows setup`, usar `llama3.2`; `phi4-mini` es opcional. No iniciar MCP en paralelo.

## Troubleshooting

| Problema | Solucion |
|----------|----------|
| `connection refused` | Ejecutar `ollama serve` en otra terminal |
| Primera respuesta lenta (~10s) | Normal — el modelo se carga a GPU la primera vez |
| Timeout >90s | El modelo no esta descargado: `ollama pull qwen3.5:35b-a3b` |
| Lento sin GPU (Linux/Windows) | Normal en modo CPU. Usar `phi4-mini` o `llama3.2` |
| Version vieja de Ollama | `brew upgrade ollama` — necesitas 0.19+ para MLX |

## Siguiente paso

Ir a [02-cluster](../02-cluster/) para crear el cluster Kubernetes.
