# Paso 6 — Portal Web (SSE)

Portal web con animaciones en tiempo real que muestra cada paso del pipeline.

## Que es

Un servidor FastAPI que ejecuta el mismo pipeline del agente CLI pero transmite eventos via **Server-Sent Events (SSE)** al browser. La UI muestra animaciones paso a paso.

## Setup

```bash
# 1. Instalar dependencias
make install

# 2. Iniciar el servidor
make run
# Abrir http://localhost:8888
```

## Arquitectura

```
Browser (index.html)
    |
    | EventSource (SSE)
    v
FastAPI (server.py)
    |
    |-- GET /                  -> sirve index.html
    |-- GET /api/deploy?prompt=...  -> pipeline SSE
    |-- GET /api/status        -> estado de servicios
    |-- GET /api/pods/{ns}     -> pods del namespace
```

## Eventos SSE

| Evento | Payload | Efecto en UI |
|--------|---------|-------------|
| `services` | `{ollama, backstage, github, kubectl}` | Badges del header |
| `intent` | `{service_name, environment, replicas, ...}` | Tarjeta de intent |
| `step_start` | `{id, msg}` | Barra de progreso + animacion |
| `step_done` | `{id, yaml?, pods?}` | Tick verde, muestra YAML/pods |
| `step_warn` | `{id, msg}` | Chip amarillo, modo degradado |
| `step_skip` | `{id, msg}` | Chip gris, servicio no disponible |
| `done` | `{service, env, replicas}` | Banner de exito |

## Personalizar

Para agregar un evento nuevo:

```python
# En server.py, dentro de pipeline_generator():
yield sse("mi_evento", {"dato": valor})

# En index.html:
es.addEventListener("mi_evento", e => {
  const data = JSON.parse(e.data);
  // hacer algo
});
```

## Siguiente paso

Ir a [07-demo](../07-demo/) para el guion completo de la demo.
