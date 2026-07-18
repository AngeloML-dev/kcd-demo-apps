#!/bin/bash
# ================================================================
# KCD Peru 2026 — Configurar ArgoCD con GitHub
# Conecta ArgoCD al repo de GitHub y crea las Applications
# Ejecutar después de: make setup
# ================================================================
set -e

BOLD='\033[1m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

step() { echo -e "\n${CYAN}${BOLD}▶ $1${NC}"; }
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════╗"
echo "║   KCD Peru 2026 — ArgoCD + GitHub Setup         ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Cargar .env ──────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  err ".env no encontrado. Ejecuta primero: cp .env.example .env"
fi

eval "$(grep -v '^#' "$ENV_FILE" | grep '=' | sed 's/^/export /')"

# ── Validar variables ────────────────────────────────────────
step "Validando configuración..."

[ -z "$GITHUB_TOKEN" ] && err "GITHUB_TOKEN no configurado en .env"
[ -z "$GITHUB_REPO" ]  && err "GITHUB_REPO no configurado en .env (ej: usuario/kcd-demo-apps)"
[[ "$GITHUB_TOKEN" == "ghp_xxx"* ]] && err "GITHUB_TOKEN tiene el valor de ejemplo — reemplázalo"
[[ "$GITHUB_REPO" == "tu-usuario"* ]] && err "GITHUB_REPO tiene el valor de ejemplo — reemplázalo"

GITHUB_USER=$(echo "$GITHUB_REPO" | cut -d'/' -f1)
GITHUB_REPO_NAME=$(echo "$GITHUB_REPO" | cut -d'/' -f2)
REPO_URL="https://github.com/${GITHUB_REPO}.git"

ok "GITHUB_REPO: $GITHUB_REPO"
ok "Repo URL:    $REPO_URL"

# ── Verificar que el repo existe en GitHub ───────────────────
step "Verificando repositorio en GitHub..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$GITHUB_REPO")

if [ "$HTTP_CODE" == "200" ]; then
  ok "Repo $GITHUB_REPO encontrado"
elif [ "$HTTP_CODE" == "404" ]; then
  warn "Repo $GITHUB_REPO no existe. Creándolo automáticamente..."
  RESPONSE=$(curl -s -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/user/repos \
    -d "{\"name\":\"$GITHUB_REPO_NAME\",\"private\":false,\"description\":\"KCD Peru 2026 — GitOps apps repo\",\"auto_init\":true}")

  if echo "$RESPONSE" | grep -q '"full_name"'; then
    ok "Repo creado: github.com/$GITHUB_REPO"
  else
    err "No se pudo crear el repo. Verifica los permisos del token (necesita 'repo')."
  fi
else
  err "Error al verificar el repo (HTTP $HTTP_CODE). Verifica el token."
fi

# ── Crear estructura de carpetas en GitHub ───────────────────
step "Creando estructura de carpetas en GitHub..."

create_folder_placeholder() {
  local path="$1"
  local message="$2"
  local content=$(echo "# KCD Demo — $path" | base64)

  HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
    -X PUT \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$GITHUB_REPO/contents/$path/.gitkeep" \
    -d "{\"message\":\"$message\",\"content\":\"$content\"}")

  if [ "$HTTP" == "201" ] || [ "$HTTP" == "200" ] || [ "$HTTP" == "422" ]; then
    ok "Carpeta: $path/"
  else
    warn "No se pudo crear $path/ (HTTP $HTTP) — puede que ya exista"
  fi
}

create_folder_placeholder "apps/staging"    "chore: init staging folder"
create_folder_placeholder "apps/production" "chore: init production folder"

# ── Instalar ArgoCD CLI si no está ──────────────────────────
step "Verificando ArgoCD CLI..."
if ! command -v argocd &>/dev/null; then
  if [ "$(uname -s)" = "Darwin" ]; then
    warn "argocd CLI no encontrado. Instalando con Homebrew..."
    brew install argocd 2>/dev/null || warn "No se pudo instalar con brew. Instala argocd manualmente."
  else
    warn "argocd CLI no encontrado; se usara el fallback con kubectl (compatible con WSL2)."
  fi
fi

if command -v argocd &>/dev/null; then
  ok "argocd CLI disponible"
else
  warn "argocd CLI no disponible — el port-forward y login se saltarán"
  SKIP_ARGOCD_CLI=true
fi

# ── Port-forward ArgoCD ──────────────────────────────────────
step "Conectando a ArgoCD..."

# Obtener password si no está en .env
if [ -z "$ARGOCD_PASSWORD" ]; then
  ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
    -o jsonpath="{.data.password}" 2>/dev/null | base64 -d 2>/dev/null || echo "")
fi

if [ -z "$ARGOCD_PASSWORD" ]; then
  err "No se pudo obtener la contraseña de ArgoCD. ¿Está instalado? Ejecuta: make setup"
fi

ok "Contraseña ArgoCD obtenida"

# Iniciar port-forward en background
kubectl port-forward svc/argocd-server -n argocd 8080:443 &>/dev/null &
PF_PID=$!
sleep 3

# Cleanup al salir
trap "kill $PF_PID 2>/dev/null; true" EXIT

if [ "${SKIP_ARGOCD_CLI}" != "true" ]; then
  # Login a ArgoCD
  argocd login localhost:8080 \
    --username admin \
    --password "$ARGOCD_PASSWORD" \
    --insecure \
    --grpc-web 2>/dev/null && ok "Login ArgoCD exitoso" || warn "Login ArgoCD falló — continuando..."

  # ── Registrar repo de GitHub en ArgoCD ──────────────────────
  step "Registrando repo GitHub en ArgoCD..."

  argocd repo add "$REPO_URL" \
    --username "$GITHUB_USER" \
    --password "$GITHUB_TOKEN" \
    --insecure \
    2>/dev/null && ok "Repo $REPO_URL registrado en ArgoCD" \
    || warn "El repo puede que ya esté registrado"

  # ── Crear ArgoCD Applications ────────────────────────────────
  step "Creando ArgoCD Applications..."

  # Application staging
  argocd app create staging-apps \
    --repo "$REPO_URL" \
    --path "apps/staging" \
    --dest-server "https://kubernetes.default.svc" \
    --dest-namespace "staging" \
    --sync-policy automated \
    --auto-prune \
    --self-heal \
    --upsert \
    --insecure \
    2>/dev/null && ok "Application 'staging-apps' creada" || warn "staging-apps ya existe"

  # Application production
  argocd app create production-apps \
    --repo "$REPO_URL" \
    --path "apps/production" \
    --dest-server "https://kubernetes.default.svc" \
    --dest-namespace "production" \
    --sync-policy automated \
    --auto-prune \
    --self-heal \
    --upsert \
    --insecure \
    2>/dev/null && ok "Application 'production-apps' creada" || warn "production-apps ya existe"

  # Listar apps
  echo ""
  argocd app list --insecure 2>/dev/null || true

else
  # Fallback: aplicar via kubectl
  step "Aplicando ArgoCD Applications via kubectl..."
  sed "s|YOUR_GITHUB_USER/kcd-demo-apps|$GITHUB_REPO|g" \
    "$SCRIPT_DIR/argocd/apps.yaml" | kubectl apply -f -
  ok "Applications aplicadas"
fi

# ── Resumen ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}🎉 ArgoCD + GitHub configurados!${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Repo GitOps:${NC}"
echo -e "  ${CYAN}https://github.com/$GITHUB_REPO${NC}"
echo ""
echo -e "  ${BOLD}ArgoCD UI:${NC}  (ejecuta en otra terminal)"
echo -e "  ${CYAN}make argocd${NC}  →  https://localhost:8080"
echo -e "  Usuario: ${BOLD}admin${NC} / Contraseña: ${BOLD}$ARGOCD_PASSWORD${NC}"
echo ""
echo -e "  ${BOLD}Flujo GitOps activo:${NC}"
echo -e "  Agente → ${CYAN}GitHub (push manifest)${NC} → ArgoCD detecta → ${CYAN}kind cluster${NC}"
echo ""
echo -e "  ${BOLD}Iniciar el demo:${NC}"
echo -e "  ${CYAN}make demo${NC}"
echo ""
