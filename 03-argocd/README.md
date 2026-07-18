# Paso 3 — ArgoCD (GitOps)

Instalar ArgoCD en el cluster y conectarlo con GitHub para el flujo GitOps.

## Que es ArgoCD

[ArgoCD](https://argo-cd.readthedocs.io/) es un controlador GitOps para Kubernetes. Observa un repositorio de GitHub y sincroniza automaticamente el cluster con los manifests que encuentra.

## Flujo GitOps

```
Agente AI
    |
    v
GitHub (push manifest YAML)
    |
    v
ArgoCD (detecta cambio, ~30s)
    |
    v
kind cluster (pods corriendo)
```

## Setup

```bash
# 1. Instalar ArgoCD en el cluster (~1 min)
make install

# 2. Configurar .env con tu GitHub token
#    (si no lo hiciste en el paso 0)
cp ../.env.example ../.env
# Editar ../.env: llenar GITHUB_TOKEN y GITHUB_REPO

# 3. Conectar ArgoCD con GitHub
make configure

# 4. Abrir la UI de ArgoCD (en otra terminal)
make ui
```

## Crear el GitHub Token

1. Ir a [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta) (Fine-grained tokens)
2. **Repository access** → "Only select repositories" → elegir tu repo `kcd-demo-apps`
3. **Permissions** → Repositories:

| Permiso | Acceso | Para que |
|---------|--------|----------|
| **Contents** | Read and write | Backstage pushea manifests YAML al repo |
| **Pull requests** | Read and write | Backstage crea PRs, el agente las mergea |
| **Metadata** | Read-only | Se agrega automatico (requerido) |

4. Click "Generate token" y copiarlo en `.env` como `GITHUB_TOKEN`

## ArgoCD UI

- **URL:** https://localhost:8080
- **Usuario:** admin
- **Password:** se muestra al ejecutar `make configure`

## Applications creadas

| Application | Observa | Namespace destino |
|-------------|---------|-------------------|
| `staging-apps` | `apps/staging/` en GitHub | staging |
| `production-apps` | `apps/production/` en GitHub | production |

Ambas con sync automatico + auto-prune + self-heal.

## Troubleshooting

| Problema | Solucion |
|----------|----------|
| `make install` falla | Verificar que el cluster kind existe: `cd ../02-cluster && make status` |
| `make configure` pide password | Ejecutar `make install` primero |
| ArgoCD no sincroniza | Token JWT expira cada 24h: `make configure` re-hace el login |
| GitHub push 403 | Token sin scope `repo`: regenerar en github.com/settings/tokens |

## Siguiente paso

Ir a [04-backstage](../04-backstage/) para instalar el IDP requerido.
