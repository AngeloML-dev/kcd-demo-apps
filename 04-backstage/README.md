# Paso 4 — Backstage (IDP)

Instalar [Backstage](https://backstage.io) como Internal Developer Platform.

> **Este paso es requerido.** Backstage es el IDP del workshop: sus Software Templates generan los manifests y crean el Pull Request en GitHub.

> **Windows con 16 GB:** `make -f Makefile.windows setup` instala Backstage. Usa `llama3.2`, asigna 6–8 GB a Docker Desktop y no ejecutes MCP en paralelo.

## Que es Backstage

Backstage es un framework de Spotify para construir portales de desarrolladores. En este demo lo usamos para:
- **Catalogo:** registrar los servicios desplegados
- **Software Templates:** generar manifests K8s a partir de templates parametrizados

## Setup

```bash
# 1. Instalar Backstage (~10 min la primera vez)
make install

# 2. Iniciar Backstage
make start
# Abrir http://localhost:3000
```

## Templates disponibles

| Template | Uso | Inputs |
|----------|-----|--------|
| `microservice-template` | Deployment + Service basico | service_name, environment, replicas, port, owner |
| `api-with-database` | API + PostgreSQL | service_name, environment, replicas, owner, db_storage |

## Configuracion

- **Auth:** Guest (sin credenciales, perfecto para demos)
- **Database:** SQLite en memoria (arranque instantaneo, sin PostgreSQL)
- **Templates:** se cargan desde archivos locales, no desde GitHub

## Troubleshooting

| Problema | Solucion |
|----------|----------|
| `make install` tarda mucho | Normal la primera vez (~10 min por TypeScript) |
| Puerto 3000 ocupado | `lsof -ti:3000 \| xargs kill` |
| Templates no aparecen | Verificar `catalog.locations` en `app-config.yaml` |

## Siguiente paso

Ir a [05-agent](../05-agent/) para configurar el agente AI.
