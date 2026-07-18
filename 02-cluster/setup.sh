#!/bin/bash
# ================================================================
# KCD Peru 2026 — Crear cluster kind
# ================================================================
set -e

BOLD='\033[1m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  OK  $1${NC}"; }
warn() { echo -e "${YELLOW}  WARN  $1${NC}"; }
err()  { echo -e "${RED}  ERROR  $1${NC}"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLUSTER_NAME="kcd-demo"
KIND_CONFIG="${KIND_CONFIG:-kind-config.yaml}"

if [[ "$KIND_CONFIG" != /* ]]; then
  KIND_CONFIG="$SCRIPT_DIR/$KIND_CONFIG"
fi

[ -f "$KIND_CONFIG" ] || err "No se encontro la configuracion kind: $KIND_CONFIG"

echo -e "${BOLD}"
echo "========================================"
echo "  KCD Peru 2026 — Crear cluster kind"
echo "========================================"
echo -e "${NC}"

# ── Verificar Docker ──────────────────────────────────────────
docker info &>/dev/null || err "Docker/OrbStack no esta corriendo. Abrelo primero."
ok "Docker/OrbStack corriendo"

# ── Verificar si ya existe ────────────────────────────────────
if kind get clusters 2>/dev/null | grep -q "$CLUSTER_NAME"; then
  warn "Cluster '$CLUSTER_NAME' ya existe"
  echo -e "  Para recrear: ${CYAN}make destroy && make create${NC}"
  exit 0
fi

# ── Crear cluster ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}=> Creando cluster kind con $(basename "$KIND_CONFIG")...${NC}"
kind create cluster --config "$KIND_CONFIG"

# ── Esperar nodos Ready ───────────────────────────────────────
echo ""
echo -e "${CYAN}=> Esperando nodos Ready...${NC}"
kubectl wait --for=condition=Ready nodes --all --timeout=120s
ok "Todos los nodos Ready"

# ── Crear namespaces ──────────────────────────────────────────
echo ""
echo -e "${CYAN}=> Creando namespaces...${NC}"
kubectl create namespace staging    2>/dev/null && ok "Namespace 'staging' creado"    || ok "Namespace 'staging' ya existe"
kubectl create namespace production 2>/dev/null && ok "Namespace 'production' creado" || ok "Namespace 'production' ya existe"

# ── Resumen ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}Cluster '$CLUSTER_NAME' listo!${NC}"
echo ""
kubectl get nodes
echo ""
echo -e "Siguiente paso: ${CYAN}cd ../03-argocd && make install${NC}"
echo ""
