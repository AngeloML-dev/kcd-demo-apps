# =======================================================
# KCD Peru 2026 — Workshop Makefile (orquestador global)
# =======================================================

.PHONY: help setup-all check demo web status clean-apps clean-all

PYTHON := python3

help: ## Mostrar todos los comandos
	@echo ""
	@echo "  KCD Peru 2026 — Platform Engineering + AI"
	@echo "  Workshop: Del YAML al lenguaje natural"
	@echo ""
	@echo "  Uso: make <comando>"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
		{printf "    \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "  == Carpetas del workshop ========================="
	@echo "    00-prerequisites/    Instalar herramientas"
	@echo "    01-ollama/           LLM local"
	@echo "    02-cluster/          Cluster Kubernetes (kind)"
	@echo "    03-argocd/           ArgoCD (GitOps)"
	@echo "    04-backstage/        Backstage IDP (requerido)"
	@echo "    05-agent/            Agente AI (CLI)"
	@echo "    06-web/              Portal web (SSE)"
	@echo "    07-demo/             Guion del demo"
	@echo "    08-mcp/              Agente con MCP (K8s + GitHub)"
	@echo ""
	@echo "  == Quick start =================================="
	@echo "    make setup-all    Ejecutar pasos 00-04 en orden"
	@echo "    Windows/WSL2: make -f Makefile.windows help"
	@echo "    make demo         Iniciar agente CLI"
	@echo "    make web          Iniciar portal web"
	@echo ""

# ── Setup completo ───────────────────────────────────────────
setup-all: ## Ejecutar pasos 00 al 04 en orden (setup completo con Backstage)
	@[ -f .env ] || cp .env.example .env
	@echo ""
	@echo "=============================="
	@echo "  Paso 0 — Prerequisites"
	@echo "=============================="
	@$(MAKE) -C 00-prerequisites check
	@$(MAKE) -C 00-prerequisites venv
	@echo ""
	@echo "=============================="
	@echo "  Paso 1 — Ollama"
	@echo "=============================="
	@$(MAKE) -C 01-ollama setup
	@echo ""
	@echo "=============================="
	@echo "  Paso 2 — Cluster kind"
	@echo "=============================="
	@$(MAKE) -C 02-cluster create
	@echo ""
	@echo "=============================="
	@echo "  Paso 3 — ArgoCD"
	@echo "=============================="
	@$(MAKE) -C 03-argocd install
	@echo ""
	@echo "=============================="
	@echo "  Paso 4 — Backstage IDP"
	@echo "=============================="
	@$(MAKE) -C 04-backstage install

# ── Shortcuts ────────────────────────────────────────────────
check: ## Verificar estado de todos los servicios
	@$(MAKE) -C 07-demo check

demo: ## Iniciar agente AI en modo CLI
	@[ -f .env ] || cp .env.example .env
	@$(MAKE) -C 05-agent run

web: ## Iniciar portal web en http://localhost:8888
	@[ -f .env ] || cp .env.example .env
	@$(MAKE) -C 06-web run

status: ## Ver pods corriendo en el cluster
	@echo ""
	@echo "== Nodos =================================================="
	@kubectl get nodes -o wide --no-headers 2>/dev/null || echo "  (cluster no disponible)"
	@echo ""
	@echo "== Pods staging ==========================================="
	@kubectl get pods -n staging -o wide --no-headers 2>/dev/null || echo "  (vacio)"
	@echo ""
	@echo "== Pods production ========================================"
	@kubectl get pods -n production -o wide --no-headers 2>/dev/null || echo "  (vacio)"
	@echo ""

# ── ArgoCD shortcut ──────────────────────────────────────────
argocd-setup: ## Conectar ArgoCD con GitHub
	@$(MAKE) -C 03-argocd configure

argocd: ## Abrir ArgoCD UI en https://localhost:8080
	@$(MAKE) -C 03-argocd ui

# ── Backstage shortcuts ─────────────────────────────────────
backstage-install: ## Instalar Backstage (~10 min)
	@$(MAKE) -C 04-backstage install

backstage: ## Iniciar Backstage en http://localhost:3000
	@$(MAKE) -C 04-backstage start

# ── MCP Agent ──────────────────────────────────────────────
mcp: ## Iniciar agente con MCP (qwen3.5:35b-a3b + K8s + GitHub)
	@[ -f .env ] || cp .env.example .env
	@$(MAKE) -C 08-mcp run

mcp-setup: ## Setup MCP (modelo + servers)
	@$(MAKE) -C 08-mcp setup

# ── Limpieza ─────────────────────────────────────────────────
clean-apps: ## Borrar deployments generados (mantiene cluster)
	@$(MAKE) -C 07-demo clean-apps

clean-all: ## Eliminar cluster kind y Backstage completos
	@$(MAKE) -C 07-demo clean-all
	@rm -rf 04-backstage/app
