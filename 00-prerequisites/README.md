# Paso 0 — Prerequisitos

Instalar las herramientas necesarias para el workshop.

## Herramientas requeridas

| Herramienta | Instalacion | Para que sirve |
|-------------|-------------|----------------|
| **OrbStack** | [orbstack.dev](https://orbstack.dev) | Runtime Docker nativo Apple Silicon. Reemplaza Docker Desktop. Solo macOS — ver alternativas abajo. |
| **kind** | `brew install kind` | Cluster Kubernetes local (1 CP + 2 workers) |
| **kubectl** | `brew install kubectl` | CLI para interactuar con Kubernetes |
| **helm** | `brew install helm` | Package manager para K8s (usado por ArgoCD) |
| **Ollama** | `brew install ollama` | LLM local — corre modelos AI en tu Mac via Metal GPU. En Linux/Windows usa CPU o CUDA. |
| **Node.js** | `brew install node` | Necesario para Backstage |
| **Python 3** | Viene con macOS / `apt install python3` en Linux | Runtime del agente AI |

> **Multiplataforma:** OrbStack es exclusivo de macOS. En **Linux** usa Docker Engine nativo. En **Windows** usa Docker Desktop o WSL2. Ver secciones de instalacion por OS mas abajo.

## Instalacion rapida

### macOS

```bash
# Instalar todo con Homebrew + crear venv Python
make install

# O manualmente:
brew install kind kubectl helm ollama node
```

> **OrbStack** se descarga desde [orbstack.dev](https://orbstack.dev). Abrirlo despues de instalarlo.

### Linux

```bash
# Docker Engine (no necesitas OrbStack ni Docker Desktop)
# Ubuntu/Debian:
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker $USER  # reiniciar sesion despues

# kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Node.js (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Python 3 (generalmente ya viene instalado)
sudo apt-get install -y python3 python3-venv python3-pip
```

### Windows

```powershell
# Opcion 1 (recomendada): WSL2 + seguir las instrucciones de Linux
wsl --install  # reiniciar, luego seguir instrucciones de Linux dentro de WSL2

# Opcion 2: nativo con Docker Desktop
# Descargar Docker Desktop desde https://www.docker.com/products/docker-desktop/
# Descargar kind: https://kind.sigs.k8s.io/docs/user/quick-start/#installation
# Descargar kubectl: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
# Descargar helm: https://helm.sh/docs/intro/install/#from-chocolatey-windows
choco install kind kubectl helm nodejs-lts python3

# Ollama para Windows
# Descargar desde https://ollama.com/download/windows
```

> **Nota Windows:** Se recomienda fuertemente usar **WSL2** ya que los scripts bash del proyecto estan disenados para entornos Unix. Si usas Windows nativo, necesitaras adaptar los scripts `.sh` o ejecutarlos con Git Bash.

## Virtualenv Python

Se crea un venv compartido en la raiz del proyecto (`.venv/`) con todas las dependencias de `05-agent` y `06-web`.

```bash
# Crear el venv (incluido en make install)
make venv

# Las carpetas 05-agent y 06-web lo usan automaticamente
```

## Configurar .env

```bash
cp ../.env.example ../.env
```

Editar `../.env` y llenar:

- **`GITHUB_TOKEN`** — Fine-grained token de GitHub ([crear aqui](https://github.com/settings/tokens?type=beta))
- **`GITHUB_REPO`** — tu repo GitOps (ej: `tu-usuario/kcd-demo-apps`)

### Permisos del GitHub Token

1. **Repository access** → "Only select repositories" → elegir tu repo
2. **Permissions** → Repositories:

| Permiso | Acceso | Para que |
|---------|--------|----------|
| **Contents** | Read and write | Backstage pushea manifests YAML |
| **Pull requests** | Read and write | Backstage crea PRs, agente las mergea |
| **Metadata** | Read-only | Se agrega automatico |

## Verificar

```bash
make check
```

Debe mostrar OK para todas las herramientas incluyendo el venv.

## Siguiente paso

Ir a [01-ollama](../01-ollama/) para configurar el LLM local.
