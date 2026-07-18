# Paso 2 — Cluster kind
.PHONY: help create create-lite status destroy

CLUSTER_NAME := kcd-demo

help: ## Mostrar ayuda
	@echo ""
	@echo "  Paso 2 — Cluster Kubernetes (kind)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
		{printf "    \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

create: ## Crear cluster kind (1 CP + 2 workers, ~2 min)
	@chmod +x setup.sh
	@bash setup.sh

create-lite: ## Crear cluster liviano (solo control-plane, recomendado para Windows 16 GB)
	@chmod +x setup.sh
	@KIND_CONFIG=kind-config.windows-16gb.yaml bash setup.sh

status: ## Ver estado del cluster y nodos
	@echo ""
	@kind get clusters 2>/dev/null | grep -q "$(CLUSTER_NAME)" && \
		echo "  OK  Cluster '$(CLUSTER_NAME)' existe" || \
		{ echo "  WARN  Cluster no existe -> make create"; exit 0; }
	@echo ""
	@kubectl get nodes -o wide 2>/dev/null || echo "  (no se puede conectar al cluster)"
	@echo ""
	@echo "== Namespaces =="
	@kubectl get namespaces 2>/dev/null | grep -E "staging|production" || echo "  (no creados aun)"
	@echo ""

destroy: ## Eliminar cluster kind completo
	@echo "=> Eliminando cluster '$(CLUSTER_NAME)'..."
	@kind delete cluster --name $(CLUSTER_NAME) 2>/dev/null || true
	@echo "  OK  Cluster eliminado"
