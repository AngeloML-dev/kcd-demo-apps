# Paso 4 — Backstage IDP (requerido)
.PHONY: help install start status

BACKSTAGE_DIR := app

help: ## Mostrar ayuda
	@echo ""
	@echo "  Paso 4 — Backstage IDP (requerido)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
		{printf "    \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

install: ## Instalar Backstage (~10 min la primera vez)
	@chmod +x install.sh
	@bash install.sh

start: ## Iniciar Backstage en http://localhost:3000
	@echo ""
	@echo "  Backstage -> http://localhost:3000  (Ctrl+C para cerrar)"
	@echo ""
	@if [ ! -d "$(BACKSTAGE_DIR)" ]; then \
		echo "  ERROR  Backstage no instalado -> make install"; \
		exit 1; \
	fi
	@set -a && eval "$$(grep -v '^#' $(shell cd .. && pwd)/.env | grep '=')" && set +a && cd $(BACKSTAGE_DIR) && NODE_OPTIONS=--no-node-snapshot yarn start 2>&1

status: ## Verificar estado de Backstage
	@curl -sf http://localhost:7007/api/catalog/entities &>/dev/null && \
		echo "  OK  Backstage corriendo en http://localhost:3000" || \
		echo "  WARN  Backstage no esta corriendo -> make start"
