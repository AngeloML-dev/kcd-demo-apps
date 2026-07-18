# Paso 0 — Prerequisitos
.PHONY: help install check venv

ROOT_DIR := $(shell cd .. && pwd)
VENV     := $(ROOT_DIR)/.venv

help: ## Mostrar ayuda
	@echo ""
	@echo "  Paso 0 — Prerequisitos"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
		{printf "    \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

install: venv ## Instalar herramientas con Homebrew + crear venv Python
	@echo "=> Instalando herramientas..."
	@brew install kind kubectl helm ollama node 2>/dev/null || true
	@echo ""
	@echo "=> No olvides instalar OrbStack desde https://orbstack.dev"
	@echo ""
	@$(MAKE) check

venv: ## Crear virtualenv Python en la raiz del proyecto
	@if [ ! -d "$(VENV)" ]; then \
		echo "=> Creando virtualenv en $(VENV)..."; \
		python3 -m venv $(VENV); \
		$(VENV)/bin/pip install --upgrade pip -q; \
		$(VENV)/bin/pip install -r $(ROOT_DIR)/05-agent/requirements.txt -q; \
		$(VENV)/bin/pip install -r $(ROOT_DIR)/06-web/requirements.txt -q; \
		echo "  OK  Virtualenv creado con todas las dependencias"; \
	else \
		echo "  OK  Virtualenv ya existe en $(VENV)"; \
	fi

check: ## Verificar que todas las herramientas estan instaladas
	@echo ""
	@echo "== Verificando herramientas =========================="
	@echo ""
	@command -v docker  &>/dev/null && \
		echo "  OK  Docker/OrbStack" || \
		echo "  FALTA  Docker/OrbStack -> descargar en orbstack.dev"
	@command -v kind    &>/dev/null && \
		echo "  OK  kind:    $$(kind version 2>/dev/null | head -c 30)" || \
		echo "  FALTA  kind    -> ver instrucciones para tu OS en README.md"
	@command -v kubectl &>/dev/null && \
		echo "  OK  kubectl: $$(kubectl version --client -o json 2>/dev/null | grep gitVersion | head -1 | cut -d'"' -f4)" || \
		echo "  FALTA  kubectl -> ver instrucciones para tu OS en README.md"
	@command -v helm    &>/dev/null && \
		echo "  OK  helm:    $$(helm version --short 2>/dev/null)" || \
		echo "  FALTA  helm    -> ver instrucciones para tu OS en README.md"
	@command -v ollama  &>/dev/null && \
		echo "  OK  ollama:  instalado" || \
		echo "  FALTA  ollama  -> ver instrucciones para tu OS en README.md"
	@command -v node    &>/dev/null && \
		echo "  OK  node:    $$(node --version)" || \
		echo "  FALTA  node    -> ver instrucciones para tu OS en README.md"
	@command -v python3 &>/dev/null && \
		echo "  OK  python3: $$(python3 --version 2>&1)" || \
		echo "  FALTA  python3 -> viene con macOS"
	@[ -d "$(VENV)" ] && \
		echo "  OK  venv:    $(VENV)" || \
		echo "  FALTA  venv    -> make venv"
	@echo ""
