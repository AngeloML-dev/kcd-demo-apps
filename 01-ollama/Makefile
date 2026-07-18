# Paso 1 — Ollama
.PHONY: help setup start test check

ROOT_DIR     := $(shell cd .. && pwd)
-include $(ROOT_DIR)/.env
OLLAMA_MODEL ?= llama3.2

# Flash Attention + optimizaciones Metal (M4) o MLX nativo (M5+)
export OLLAMA_NEW_ENGINE ?= 1

help: ## Mostrar ayuda
	@echo ""
	@echo "  Paso 1 — Ollama (LLM local)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
		{printf "    \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

setup: ## Descargar el modelo configurado en .env
	@echo "=> Descargando modelo $(OLLAMA_MODEL)..."
	ollama pull $(OLLAMA_MODEL)
	@echo ""
	@echo "OK Modelo $(OLLAMA_MODEL) descargado"

start: ## Iniciar servidor Ollama (dejar corriendo en esta terminal)
	@if [ -d "/Applications/Ollama.app" ]; then \
		echo "=> Iniciando Ollama.app (MLX nativo)..."; \
		open -a Ollama; \
	else \
		echo "=> Ollama server en http://localhost:11434  (Ctrl+C para cerrar)"; \
		OLLAMA_NEW_ENGINE=$(OLLAMA_NEW_ENGINE) ollama serve; \
	fi

test: ## Probar que Ollama responde correctamente
	@echo "=> Probando Ollama con $(OLLAMA_MODEL)..."
	@echo ""
	@curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 || \
		{ echo "  ERROR Ollama no esta corriendo -> ollama serve"; exit 1; }
	@echo "  OK Ollama server respondiendo"
	@echo ""
	@echo "=> Enviando prompt de prueba..."
	@curl -s http://localhost:11434/api/generate \
		-d '{"model":"$(OLLAMA_MODEL)","prompt":"Return only this JSON: {\"test\": \"ok\", \"model\": \"$(OLLAMA_MODEL)\"}","stream":false}' \
		| python3 -c "import sys,json; print(json.loads(sys.stdin.read())['response'])" 2>/dev/null \
		&& echo "" && echo "  OK Modelo respondiendo correctamente" \
		|| echo "  ERROR El modelo no respondio — verifica que esta descargado: ollama pull $(OLLAMA_MODEL)"
	@echo ""

check: ## Verificar estado de Ollama
	@curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 && \
		echo "  OK Ollama corriendo en :11434" || \
		echo "  WARN Ollama no esta corriendo -> make start"
	@curl -sf http://localhost:11434/api/tags 2>/dev/null | \
		python3 -c "import sys,json; models=json.loads(sys.stdin.read()).get('models',[]); [print(f'  OK Modelo: {m[\"name\"]}') for m in models]" 2>/dev/null || true
