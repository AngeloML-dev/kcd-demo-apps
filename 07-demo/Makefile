# Paso 7 — Demo
.PHONY: help start-all check clean-apps clean-all

ROOT_DIR := $(shell cd .. && pwd)

help: ## Mostrar ayuda
	@echo ""
	@echo "  Paso 7 — Demo KCD Peru 2026"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
		{printf "    \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

start-all: ## Iniciar todos los servicios (Ollama + Backstage + Web + ArgoCD)
	@echo ""
	@echo "  Para el demo completo, abre 4 terminales:"
	@echo ""
	@echo "  Terminal 1 (LLM):      ollama serve"
	@echo "  Terminal 2 (Backstage): cd $(ROOT_DIR)/04-backstage && make start"
	@echo "  Terminal 3 (Portal):    cd $(ROOT_DIR)/06-web && make run"
	@echo "  Terminal 4 (ArgoCD):    cd $(ROOT_DIR)/03-argocd && make ui"
	@echo ""
	@echo "  O usar el agente CLI:   cd $(ROOT_DIR)/05-agent && make run"
	@echo ""

check: ## Verificar estado de todos los servicios
	@echo ""
	@echo "== Cluster ================================================"
	@kind get clusters 2>/dev/null | grep -q "kcd-demo" && \
		echo "  OK  Cluster kcd-demo existe" || \
		echo "  FALTA  Cluster -> cd ../02-cluster && make create"
	@kubectl get nodes --no-headers 2>/dev/null | awk \
		'{print "  OK  Nodo:", $$1, "->", $$2}' || true
	@echo ""
	@echo "== Servicios =============================================="
	@docker info &>/dev/null && \
		echo "  OK  Docker/OrbStack corriendo" || \
		echo "  FALTA  Docker/OrbStack"
	@curl -sf http://localhost:11434/api/tags &>/dev/null && \
		echo "  OK  Ollama en :11434" || \
		echo "  FALTA  Ollama -> ollama serve"
	@curl -sf http://localhost:7007/api/catalog/entities &>/dev/null && \
		echo "  OK  Backstage en :7007" || \
		echo "  FALTA  Backstage -> make backstage"
	@kubectl get svc argocd-server -n argocd &>/dev/null && \
		echo "  OK  ArgoCD instalado" || \
		echo "  FALTA  ArgoCD -> cd ../03-argocd && make install"
	@echo ""
	@echo "== Pods ==================================================="
	@echo "  -- staging --"
	@kubectl get pods -n staging --no-headers 2>/dev/null || echo "  (vacio)"
	@echo "  -- production --"
	@kubectl get pods -n production --no-headers 2>/dev/null || echo "  (vacio)"
	@echo ""

clean-apps: ## Borrar deployments generados (mantiene cluster)
	@echo "=> Eliminando deployments..."
	@kubectl delete all -l managed-by=backstage-scaffolder -n staging   2>/dev/null || true
	@kubectl delete all -l managed-by=backstage-scaffolder -n production 2>/dev/null || true
	@rm -f $(ROOT_DIR)/apps/deployed/*.yaml
	@echo "  OK  Apps eliminadas"

clean-all: ## Eliminar cluster kind completo
	@echo "=> Eliminando cluster..."
	@kind delete cluster --name kcd-demo 2>/dev/null || true
	@echo "  OK  Cluster eliminado"
