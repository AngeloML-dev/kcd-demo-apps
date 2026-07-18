# Paso 6 — Portal Web
.PHONY: help install run

ROOT_DIR := $(shell cd .. && pwd)
VENV     := $(ROOT_DIR)/.venv
PYTHON   := $(VENV)/bin/python3
PIP      := $(VENV)/bin/pip

help: ## Mostrar ayuda
	@echo ""
	@echo "  Paso 6 — Portal Web (SSE)"
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

run: install ## Iniciar portal web en http://localhost:8888
	@echo ""
	@[ -f $(ROOT_DIR)/.env ] || { echo "  ERROR  Falta .env -> cp .env.example .env (en la raiz)"; exit 1; }
	@echo "  Portal web -> http://localhost:8888  (Ctrl+C para cerrar)"
	@echo ""
	@$(PYTHON) -m uvicorn server:app --host 0.0.0.0 --port 8888 --reload
