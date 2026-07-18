#!/bin/bash
# ================================================================
# KCD Peru 2026 — Instalar ArgoCD en el cluster kind
# ================================================================
set -e

BOLD='\033[1m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  OK  $1${NC}"; }
warn() { echo -e "${YELLOW}  WARN  $1${NC}"; }
err()  { echo -e "${RED}  ERROR  $1${NC}"; exit 1; }

echo -e "${BOLD}"
echo "========================================"
echo "  KCD Peru 2026 — Instalar ArgoCD"
echo "========================================"
echo -e "${NC}"

# ── Verificar cluster ─────────────────────────────────────────
kubectl cluster-info --request-timeout=5s &>/dev/null || \
  err "No hay cluster activo. Ejecuta primero: cd ../02-cluster && make create"
ok "Cluster activo"

# ── Crear namespace argocd ────────────────────────────────────
kubectl create namespace argocd 2>/dev/null && ok "Namespace 'argocd' creado" || ok "Namespace 'argocd' ya existe"

# ── Instalar ArgoCD ───────────────────────────────────────────
echo ""
echo -e "${CYAN}=> Instalando ArgoCD...${NC}"
kubectl apply -n argocd --server-side=true --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# ── Esperar pods Ready ────────────────────────────────────────
echo ""
echo -e "${CYAN}=> Esperando pods de ArgoCD...${NC}"
kubectl wait --for=condition=Available deployment/argocd-server -n argocd --timeout=180s
ok "ArgoCD server listo"

# ── Obtener password ──────────────────────────────────────────
echo ""
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" 2>/dev/null | base64 -d 2>/dev/null || echo "")

if [ -n "$ARGOCD_PASSWORD" ]; then
  ok "Password de ArgoCD obtenido"
  echo ""
  echo -e "  ${BOLD}ArgoCD UI:${NC}  https://localhost:8080"
  echo -e "  ${BOLD}Usuario:${NC}    admin"
  echo -e "  ${BOLD}Password:${NC}   $ARGOCD_PASSWORD"

  # Guardar en .env si existe (portable entre macOS y GNU/Linux/WSL2)
  ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env"
  if [ -f "$ENV_FILE" ]; then
    ENV_TMP="${ENV_FILE}.tmp"
    awk -v password="$ARGOCD_PASSWORD" '
      /^ARGOCD_PASSWORD=/ { print "ARGOCD_PASSWORD=" password; found=1; next }
      { print }
      END { if (!found) print "ARGOCD_PASSWORD=" password }
    ' "$ENV_FILE" > "$ENV_TMP"
    mv "$ENV_TMP" "$ENV_FILE"
    ok "Password guardado en .env"
  fi
else
  warn "No se pudo obtener el password de ArgoCD"
fi

echo ""
echo -e "${GREEN}${BOLD}ArgoCD instalado!${NC}"
echo ""
echo -e "Para abrir la UI: ${CYAN}make argocd${NC}  (o ${CYAN}make ui${NC} desde 03-argocd/)"
echo -e "Para conectar GitHub: ${CYAN}make argocd-setup${NC}  (o ${CYAN}make configure${NC} desde 03-argocd/)"
echo ""
