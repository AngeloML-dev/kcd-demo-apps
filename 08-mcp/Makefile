# Paso 8 — MCP: Superpoderes para el Agente
.PHONY: help install setup-model setup-mcp run check

ROOT_DIR := $(shell cd .. && pwd)
VENV     := $(ROOT_DIR)/.venv
PYTHON   := $(VENV)/bin/python3
PIP      := $(VENV)/bin/pip

MCP_MODEL := qwen3.5:35b-a3b

help: ## Mostrar ayuda
	@echo ""
	@echo "  Paso 8 — MCP: Superpoderes para el Agente"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
		{printf "    \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

install: ## Instalar dependencias Python (MCP SDK)
	@if [ ! -d "$(VENV)" ]; then \
		echo "  WARN  Venv no existe -> creando desde 00-prerequisites..."; \
		$(MAKE) -C $(ROOT_DIR)/00-prerequisites venv; \
	fi
	@$(PIP) install -r requirements.txt -q
	@echo "  OK  Dependencias instaladas (MCP SDK incluido)"

setup-model: ## Descargar qwen3.5:35b-a3b para function calling
	@echo "  Descargando $(MCP_MODEL) (~18 GB)..."
	@echo "  NOTA: Esto puede tomar varios minutos la primera vez"
	@ollama pull $(MCP_MODEL)
	@echo "  OK  Modelo $(MCP_MODEL) listo"

setup-mcp: ## Instalar MCP servers (Kubernetes + GitHub)
	@echo "  Instalando Kubernetes MCP server..."
	@npm install -g mcp-server-kubernetes 2>/dev/null || npx mcp-server-kubernetes --help >/dev/null 2>&1 || echo "  WARN  npx se usara en runtime"
	@echo "  OK  Kubernetes MCP server listo (via npx)"
	@echo ""
	@echo "  GitHub MCP server usa Docker..."
	@docker pull ghcr.io/github/github-mcp-server 2>/dev/null || echo "  WARN  Docker pull fallo — se intentara en runtime"
	@echo "  OK  GitHub MCP server listo (via Docker)"

setup: install setup-model setup-mcp ## Setup completo (dependencias + modelo + MCP servers)

check: ## Verificar que todo esta listo
	@echo ""
	@echo "  Verificando componentes..."
	@echo ""
	@ollama list | grep -q "qwen3.5:35b-a3b" && echo "  OK  qwen3.5:35b-a3b instalado" || echo "  FAIL  qwen3.5:35b-a3b no encontrado -> make setup-model"
	@which npx >/dev/null 2>&1 && echo "  OK  npx disponible (para K8s MCP)" || echo "  FAIL  npx no encontrado -> instalar Node.js"
	@which docker >/dev/null 2>&1 && echo "  OK  docker disponible (para GitHub MCP)" || echo "  FAIL  docker no encontrado"
	@kubectl cluster-info --request-timeout=5s >/dev/null 2>&1 && echo "  OK  kubectl conectado" || echo "  FAIL  kubectl no conecta"
	@[ -f $(ROOT_DIR)/.env ] && echo "  OK  .env existe" || echo "  FAIL  .env no encontrado"
	@echo ""

run: install ## Iniciar el agente con MCP
	@echo ""
	@[ -f $(ROOT_DIR)/.env ] || { echo "  ERROR  Falta .env -> cp .env.example .env (en la raiz)"; exit 1; }
	@$(PYTHON) agent_mcp.py
