# Paso 2 — Cluster Kubernetes (kind)

Crear un cluster Kubernetes local con [kind](https://kind.sigs.k8s.io/) corriendo sobre OrbStack.

## Arquitectura del cluster

```
kind-kcd-demo
├── kcd-demo-control-plane    (control plane)
├── kcd-demo-worker           (worker 1)
└── kcd-demo-worker2          (worker 2)
```

El cluster tiene:
- **1 control-plane** con port mappings para Ingress (80, 443)
- **2 workers** para distribuir pods
- Namespaces pre-creados: `staging` y `production`

## Setup

```bash
# Crear cluster + namespaces (~2 min)
make create

# Verificar estado
make status
```

### Windows/WSL2 con 16 GB

Usa el perfil liviano, que crea solo el control-plane y reduce el consumo de Docker:

```bash
make create-lite
```

El comando global `make -f Makefile.windows setup` usa este perfil automaticamente.

## Que hace `setup.sh`

1. Crea el cluster kind usando `kind-config.yaml`
2. Espera a que todos los nodos esten `Ready`
3. Crea los namespaces `staging` y `production`

## Comandos utiles

```bash
# Ver nodos
kubectl get nodes

# Ver pods en todos los namespaces
kubectl get pods -A

# Informacion del cluster
kubectl cluster-info
```

## Docker runtime por plataforma

| Plataforma | Runtime | Notas |
|------------|---------|-------|
| **macOS** | [OrbStack](https://orbstack.dev) (recomendado) o Docker Desktop | OrbStack es mas ligero en Apple Silicon |
| **Linux** | Docker Engine nativo | `sudo apt install docker.io` o equivalente. No necesitas Docker Desktop. |
| **Windows** | Docker Desktop con integracion WSL2 | Ejecutar `make` desde WSL2; asignar 6–8 GB a Docker Desktop. |

> **kind** funciona igual en las tres plataformas — solo necesita un runtime Docker compatible.

## Troubleshooting

| Problema | Solucion |
|----------|----------|
| `Cannot connect to the Docker daemon` | **macOS:** Abrir OrbStack. **Linux:** `sudo systemctl start docker`. **Windows:** Abrir Docker Desktop. |
| `cluster already exists` | `make destroy` y luego `make create` |
| Nodos en `NotReady` | Esperar ~30s, Docker esta descargando imagenes |

## Limpiar

```bash
make destroy    # elimina el cluster completo
```

## Siguiente paso

Ir a [03-argocd](../03-argocd/) para instalar ArgoCD.
