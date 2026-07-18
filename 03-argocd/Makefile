# Paso 3 — ArgoCD
.PHONY: help install configure ui status

ROOT_DIR := $(shell cd .. && pwd)

help: ## Mostrar ayuda
	@echo ""
	@echo "  Paso 3 — ArgoCD (GitOps)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
		{printf "    \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

install: ## Instalar ArgoCD en el cluster kind
	@chmod +x install.sh
	@bash install.sh

configure: ## Conectar ArgoCD con GitHub y crear Applications
	@[ -f $(ROOT_DIR)/.env ] || { echo "  ERROR  Falta .env -> cp ../.env.example ../.env"; exit 1; }
	@chmod +x configure-argocd.sh
	@bash configure-argocd.sh

ui: ## Abrir ArgoCD UI en https://localhost:8080
	@echo "=> ArgoCD UI en https://localhost:8080  (Ctrl+C para cerrar)"
	@echo "   Usuario: admin"
	@kubectl port-forward svc/argocd-server -n argocd 8080:443

status: ## Ver estado de ArgoCD
	@echo ""
	@kubectl get pods -n argocd --no-headers 2>/dev/null | grep -v Completed && \
		echo "" || echo "  ArgoCD no esta instalado -> make install"
	@echo ""
