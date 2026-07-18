#!/bin/bash
# ================================================================
# KCD Peru 2026 — Instalar Backstage
# ================================================================
set -e

BOLD='\033[1m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  OK  $1${NC}"; }
warn() { echo -e "${YELLOW}  WARN  $1${NC}"; }
err()  { echo -e "${RED}  ERROR  $1${NC}"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/app"

echo -e "${BOLD}"
echo "========================================"
echo "  KCD Peru 2026 — Instalar Backstage"
echo "========================================"
echo -e "${NC}"

# ── Verificar Node ────────────────────────────────────────────
command -v node &>/dev/null || err "Node.js no instalado -> brew install node"
ok "Node.js $(node --version)"

# ── Verificar si ya esta instalado ────────────────────────────
if [ -d "$APP_DIR" ]; then
  warn "Backstage ya esta instalado en $APP_DIR"
  echo -e "  Para reinstalar: ${CYAN}rm -rf app && make install${NC}"
  exit 0
fi

# ── Crear app con npx ────────────────────────────────────────
echo ""
echo -e "${CYAN}=> Creando app Backstage (esto toma ~10 min)...${NC}"
cd "$SCRIPT_DIR"
echo "app" | npx @backstage/create-app@latest --skip-install 2>/dev/null || \
  echo "app" | npx @backstage/create-app@latest

# ── Copiar config personalizado ──────────────────────────────
if [ -f "$APP_DIR/app-config.yaml" ]; then
  cp "$APP_DIR/app-config.yaml" "$APP_DIR/app-config.yaml.bak"
fi
cp "$SCRIPT_DIR/app-config.yaml" "$APP_DIR/app-config.yaml"
ok "Config personalizado copiado"

# ── Registrar plugins frontend adicionales ───────────────────
# create-app instala el componente NotificationsSidebarItem, pero en la
# arquitectura frontend actual este tambien requiere registrar su plugin.
APP_ENTRY="$APP_DIR/packages/app/src/App.tsx"
if ! grep -q "@backstage/plugin-notifications/alpha" "$APP_ENTRY"; then
  sed -i.bak "/import catalogPlugin from '@backstage\/plugin-catalog\/alpha';/a\\
import notificationsPlugin from '@backstage/plugin-notifications/alpha';" "$APP_ENTRY"
  sed -i.bak "s/features: \[catalogPlugin, navModule\]/features: [catalogPlugin, notificationsPlugin, navModule]/" "$APP_ENTRY"
  rm -f "$APP_ENTRY.bak"
  ok "Plugin frontend de notificaciones registrado"
fi

# El catalogo se monta en /catalog; la raiz debe llevar alli al abrir el portal.
if ! grep -q "const homePage = PageBlueprint.make" "$APP_ENTRY"; then
  sed -i.bak "/import { createApp } from '@backstage\/frontend-defaults';/a\\
import { createFrontendModule, PageBlueprint } from '@backstage/frontend-plugin-api';" "$APP_ENTRY"
  sed -i.bak "/import { navModule } from '.\/modules\/nav';/a\\
import { Navigate } from 'react-router-dom';\\
\\
const homePage = PageBlueprint.make({\\
  params: {\\
    path: '/',\\
    loader: () => Promise.resolve(<Navigate to=\"/catalog\" replace />),\\
    noHeader: true,\\
  },\\
});\\
\\
const appModule = createFrontendModule({\\
  pluginId: 'app',\\
  extensions: [homePage],\\
});" "$APP_ENTRY"
  sed -i.bak "s/features: \[catalogPlugin, notificationsPlugin, navModule\]/features: [catalogPlugin, notificationsPlugin, appModule, navModule]/" "$APP_ENTRY"
  rm -f "$APP_ENTRY.bak"
  ok "Redireccion inicial al catalogo registrada"
fi

# El backend ya registra Scaffolder; instalar tambien su plugin frontend para
# que /create y los Software Templates sean accesibles desde el portal.
if ! grep -q "@backstage/plugin-scaffolder/alpha" "$APP_ENTRY"; then
  sed -i.bak "/import notificationsPlugin from '@backstage\/plugin-notifications\/alpha';/a\\
import scaffolderPlugin from '@backstage/plugin-scaffolder/alpha';" "$APP_ENTRY"
  sed -i.bak "s/features: \[catalogPlugin, notificationsPlugin, appModule, navModule\]/features: [catalogPlugin, notificationsPlugin, scaffolderPlugin, appModule, navModule]/" "$APP_ENTRY"
  rm -f "$APP_ENTRY.bak"
  ok "Plugin frontend de Software Templates registrado"
fi

# ── Instalar dependencias ────────────────────────────────────
echo ""
echo -e "${CYAN}=> Instalando dependencias (yarn install)...${NC}"
cd "$APP_DIR"
yarn install

echo ""
echo -e "${GREEN}${BOLD}Backstage instalado!${NC}"
echo ""
echo -e "Para iniciar: ${CYAN}make start${NC}"
echo -e "Abrir: ${CYAN}http://localhost:3000${NC}"
echo ""
