# Paso 5 — Agente AI
.PHONY: help install run

ROOT_DIR := $(shell cd .. && pwd)
VENV     := $(ROOT_DIR)/.venv
PYTHON   := $(VENV)/bin/python3
PIP      := $(VENV)/bin/pip

help: ## Mostrar ayuda
	@echo ""
	@echo "  Paso 5 — Agente AI (CLI)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
		{printf "    \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

install: ## Instalar dependencias en el venv compartido
	@if [ ! -d "$(VENV)" ]; then \
		echo "  WARN  Venv no existe -> creando desde 00-prerequisites..."; \
		$(MAKE) -C $(ROOT_DIR)/00-prerequisites venv; \
	fi
	@$(PIP) install -r requirements.txt -q
	@echo "  OK  Dependencias instaladas en $(VENV)"

run: install ## Iniciar el agente AI en modo CLI
	@echo ""
	@[ -f $(ROOT_DIR)/.env ] || { echo "  ERROR  Falta .env -> cp .env.example .env (en la raiz)"; exit 1; }
	@$(PYTHON) agent.py
