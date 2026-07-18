"""Clasificacion de intent y extraccion de parametros via Ollama."""
import json
import re
from typing import Generator
import requests
from .config import get_config

# ── Contexto del sistema para respuestas conversacionales ───
SYSTEM_CONTEXT = """Eres el asistente IA del portal KCD Peru 2026 — Platform Engineering con IA.
Respondes en espanol, de forma concisa y practica (maximo 4-5 oraciones).

== QUE ES ESTA DEMO ==
Un sistema que permite desplegar microservicios en Kubernetes usando lenguaje natural.
El usuario solo describe lo que necesita y el sistema ejecuta todo automaticamente en 5 pasos:

  Paso 1 — OLLAMA (LLM local): Interpreta el mensaje del usuario y extrae los parametros
           del deployment (nombre, replicas, ambiente, puerto, base de datos, owner).
  Paso 2 — BACKSTAGE + GITHUB: Backstage usa el Scaffolder API
           (template "microservice-template" o "api-with-database") para generar los
           manifests YAML y crear un Pull Request en GitHub.
           Los manifests se guardan en: apps/{ambiente}/{nombre-servicio}.yaml
           La rama del PR es: deploy/{nombre}-{ambiente}
  Paso 3 — GITHUB MERGE: El PR se auto-mergea a main con squash merge.
  Paso 4 — ARGOCD (GitOps): Detecta el cambio en main y sincroniza el cluster.
           Las apps en ArgoCD se llaman: staging-apps y production-apps.
  Paso 5 — KUBERNETES: Los pods quedan corriendo en el cluster kind.
           Se verifica con: kubectl get deployment {nombre} -n {ambiente}

== QUE GENERA EL SISTEMA ==
Por cada deployment se crean estos recursos Kubernetes:
- Deployment: imagen nginx:alpine, con resources requests/limits configurados
- Service: tipo ClusterIP, puerto 80 apuntando al puerto del contenedor
- HPA (HorizontalPodAutoscaler): escala automatico entre las replicas pedidas y 10, basado en CPU al 80%
- Si el usuario pide base de datos: Deployment + Service adicional de PostgreSQL (postgres:16-alpine) o MySQL

== QUE PUEDE HACER EL USUARIO ==
1. DESPLEGAR servicios nuevos escribiendo una orden directa (no pregunta). Ejemplos:
   - "despliega una API de pagos en produccion con 3 replicas"
   - "crea un servicio de usuarios con PostgreSQL en staging"
   - "levanta un nginx en produccion en el puerto 3000"
   - "necesito un backend de ordenes con mysql y 4 replicas en staging"
2. CONFIGURAR cada deployment:
   - Ambientes disponibles: staging, production (default: staging)
   - Replicas: cualquier numero (default: 1)
   - Puerto: cualquier numero (default: 8080)
   - Base de datos: PostgreSQL o MySQL (default: sin DB)
   - Owner: backend-team, platform-team, data-team, frontend-team (default: backend-team)
3. CONFIRMAR o MODIFICAR: despues de extraer los parametros, puede confirmar (si),
   cancelar (no), o escribir cambios ("cambia a produccion y 5 replicas")
4. Ver pods corriendo: escribir "status"
5. PREGUNTAR sobre Kubernetes, kubectl, Platform Engineering, GitOps, ArgoCD, Backstage

== STACK TECNOLOGICO ==
- LLM: Ollama con modelo qwen3.5 (MoE 35B, 3.5B activos) corriendo local en Apple Silicon
- Cluster: kind (Kubernetes in Docker) — cluster local para desarrollo
- GitOps: ArgoCD sincroniza automaticamente desde el repo de GitHub
- IDP: Backstage como Internal Developer Portal con Scaffolder API
- Repo de manifests: GitHub (apps/staging/ y apps/production/)
- Agente CLI: Python + Rich (este chat)
- Portal Web: FastAPI + SSE en puerto 8888 (alternativa al CLI)
- Agente MCP: version avanzada con function calling para operar el cluster

== REGLAS DE RESPUESTA ==
- Responde SIEMPRE en espanol
- Maximo 4-5 oraciones por respuesta
- Para desplegar, el usuario debe escribirlo como orden directa, no como pregunta
- Si preguntan por kubectl, da el comando exacto con namespace staging o production
- Si preguntan "como despliego" o "que puedo hacer", explica que solo escriban lo que necesitan
- NO inventes nombres de pods o servicios, usa placeholders como <nombre-del-pod>
- Si preguntan algo que no sabes, dilo honestamente"""


def classify_intent(user_message: str) -> str:
    """Clasifica el mensaje como 'deploy' o 'chat'."""
    cfg = get_config()
    prompt = f"""Task: classify this message as "deploy" or "chat". Answer with ONE word ONLY. No explanation.

deploy = the user gives a DIRECT ORDER to CREATE, DEPLOY, or LAUNCH a NEW service, application, container, or workload on Kubernetes RIGHT NOW. The message must be an imperative command or explicit request to create something new.
chat = EVERYTHING else. This includes:
  - Greetings, farewells, small talk
  - QUESTIONS about deploying (e.g. "como despliego...", "que necesito para crear...", "se puede desplegar...")
  - Asking for help, explanations, or concepts
  - Listing, viewing, checking, or describing existing resources
  - Troubleshooting, monitoring, status checks
  - Scaling, restarting, deleting, or modifying EXISTING resources
  - Viewing logs, events, or metrics
  - Any message that contains a question mark (?)
  - Talking ABOUT services without requesting to create one

CRITICAL: A question about deployment is NOT a deploy. Only classify as "deploy" when the user is explicitly commanding you to create something new. Examples:
  "despliega un nginx en produccion" → deploy
  "crea una API de pagos con postgres" → deploy
  "necesito un servicio de notificaciones en staging" → deploy
  "como despliego un servicio?" → chat
  "que es un deployment?" → chat
  "puedes desplegar cosas?" → chat
  "quiero saber sobre deployments" → chat
  "hola" → chat
  "reinicia el pod de pagos" → chat
  "escala el servicio a 5 replicas" → chat
  "muestra los pods en staging" → chat

When in doubt, answer "chat". It is better to ask the user than to deploy something they didn't want.

Message: "{user_message}"
Answer:"""

    try:
        resp = requests.post(
            f"{cfg['OLLAMA_URL']}/api/generate",
            json={"model": cfg["OLLAMA_MODEL"], "prompt": prompt,
                  "stream": False, "think": cfg.get("OLLAMA_THINK", False), "options": {"temperature": 0.0}},
            timeout=15
        )
        resp.raise_for_status()
        raw = resp.json()["response"].strip().lower()
        return "deploy" if raw.startswith("deploy") else "chat"
    except Exception:
        return "chat"


def chat_response(user_message: str) -> str:
    """Genera respuesta conversacional sobre Kubernetes."""
    cfg = get_config()
    prompt = f"""{SYSTEM_CONTEXT}

User: {user_message}
Assistant:"""

    try:
        resp = requests.post(
            f"{cfg['OLLAMA_URL']}/api/generate",
            json={"model": cfg["OLLAMA_MODEL"], "prompt": prompt,
                  "stream": False, "think": cfg.get("OLLAMA_THINK", False), "options": {"temperature": 0.7}},
            timeout=60
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
    except Exception:
        return "Hola! Puedo ayudarte a desplegar servicios en Kubernetes. Dime que necesitas."


def extract_intent(user_message: str) -> dict:
    """Extrae parametros de deployment del mensaje del usuario."""
    cfg = get_config()
    prompt = f"""You are a JSON extraction engine. Extract deployment parameters from the user message and return ONLY a valid JSON object. No markdown, no explanation, no extra text — just the JSON.

User message: "{user_message}"

Examples:

Input: "despliega un servicio de pagos en produccion con 3 replicas"
Output: {{"service_name": "pagos", "replicas": 3, "environment": "production", "port": 8080, "has_database": false, "db_type": "none", "owner": "backend-team", "description": "servicio de pagos"}}

Input: "crea una API de usuarios con PostgreSQL en staging"
Output: {{"service_name": "usuarios", "replicas": 1, "environment": "staging", "port": 8080, "has_database": true, "db_type": "postgresql", "owner": "backend-team", "description": "API de usuarios con PostgreSQL"}}

Input: "levanta un nginx con 5 replicas en produccion en el puerto 3000"
Output: {{"service_name": "nginx", "replicas": 5, "environment": "production", "port": 3000, "has_database": false, "db_type": "none", "owner": "platform-team", "description": "servidor nginx"}}

Input: "necesito un backend de ordenes con mysql y 4 replicas en staging"
Output: {{"service_name": "ordenes", "replicas": 4, "environment": "staging", "port": 8080, "has_database": true, "db_type": "mysql", "owner": "backend-team", "description": "backend de ordenes con MySQL"}}

Rules:
- service_name: lowercase, hyphens only, no spaces, no special chars. Extract the CORE noun (e.g. "API de usuarios" → "usuarios", "microservicio de pagos" → "pagos", "backend de ordenes" → "ordenes", "servicio de auth" → "auth"). NEVER leave empty.
- replicas: integer from user message. Default: 1
- environment: ONLY "staging" or "production". Map "prod"/"produccion" → "production", "stage"/"dev"/"desarrollo" → "staging". Default: "staging"
- port: integer from user message. Default: 8080
- has_database: true ONLY if user explicitly mentions: database, DB, base de datos, postgres, postgresql, mysql, mariadb, mongo, redis, sqlite
- db_type: "postgresql" (for postgres/pg/postgresql), "mysql" (for mysql/mariadb), or "none"
- owner: "backend-team" (APIs, services, workers, microservices), "platform-team" (infra, nginx, proxy, gateway, ingress), "data-team" (data pipelines, ETL, analytics, ML), "frontend-team" (BFF, frontend, web, UI). Default: "backend-team"
- description: brief description in the SAME language as the user message (max 8 words)

Output ONLY the JSON object, nothing else:"""

    defaults = {
        "service_name": "", "replicas": 1,
        "environment": "staging", "port": 8080,
        "has_database": False, "db_type": "none",
        "owner": "backend-team", "description": "servicio de demo"
    }

    try:
        resp = requests.post(
            f"{cfg['OLLAMA_URL']}/api/generate",
            json={"model": cfg["OLLAMA_MODEL"], "prompt": prompt,
                  "stream": False, "think": cfg.get("OLLAMA_THINK", False), "options": {"temperature": 0.1}},
            timeout=90
        )
        resp.raise_for_status()
        raw = resp.json()["response"].strip()

        for m in ["```json", "```"]:
            if m in raw:
                raw = raw.split(m)[1].split("```")[0].strip()
                break

        s, e = raw.find("{"), raw.rfind("}") + 1
        if s != -1 and e > s:
            raw = raw[s:e]

        parsed = json.loads(raw)
        for k, v in defaults.items():
            parsed.setdefault(k, v)

        if not parsed.get("port") or parsed["port"] <= 0:
            parsed["port"] = 8080
        if not parsed.get("replicas") or parsed["replicas"] <= 0:
            parsed["replicas"] = 1
        if parsed.get("environment") not in ("staging", "production"):
            parsed["environment"] = "staging"

        parsed["service_name"] = (
            re.sub(r"[^a-z0-9-]", "-", parsed["service_name"].lower()).strip("-")
        )
        return parsed
    except Exception:
        return dict(defaults)


def get_missing_fields(intent: dict) -> list[dict]:
    """Retorna lista de campos requeridos que faltan en el intent.
    Cada elemento: {"field": nombre, "prompt": pregunta para el usuario}."""
    missing = []
    if not intent.get("service_name"):
        missing.append({
            "field": "service_name",
            "prompt": "¿Cual es el nombre del servicio? (solo minusculas, numeros y guiones)",
        })
    return missing


def apply_field(intent: dict, field: str, value: str) -> dict:
    """Aplica el valor de un campo al intent."""
    value = value.strip()
    if field == "service_name":
        intent["service_name"] = (
            re.sub(r"[^a-z0-9-]", "-", value.lower()).strip("-") or ""
        )
    else:
        intent[field] = value
    return intent


def adjust_intent(intent: dict, user_adjustment: str) -> dict | None:
    """Usa Ollama para re-interpretar un intent con cambios del usuario."""
    cfg = get_config()
    prompt = f"""You are a JSON editor. You will receive a deployment configuration and a user modification request. Apply ONLY the requested changes and return the updated JSON. Do NOT add or remove fields. Do NOT change fields the user did not mention.

Current configuration:
{json.dumps(intent, indent=2)}

User modification: "{user_adjustment}"

Rules:
- ONLY modify fields explicitly mentioned by the user
- Keep all other fields exactly as they are
- service_name must be lowercase with hyphens only
- environment must be "staging" or "production"
- replicas must be a positive integer
- port must be a positive integer
- Return ONLY the valid JSON object, no extra text

Output:"""

    try:
        resp = requests.post(
            f"{cfg['OLLAMA_URL']}/api/generate",
            json={"model": cfg["OLLAMA_MODEL"], "prompt": prompt,
                  "stream": False, "think": cfg.get("OLLAMA_THINK", False), "options": {"temperature": 0.1}},
            timeout=60
        )
        resp.raise_for_status()
        raw = resp.json()["response"].strip()
        s, e = raw.find("{"), raw.rfind("}") + 1
        if s != -1 and e > s:
            updated = json.loads(raw[s:e])
            for k in intent:
                if k in updated:
                    intent[k] = updated[k]
            return intent
    except Exception:
        pass
    return None


def stream_chat_response(user_message: str) -> Generator[str, None, None]:
    """Genera respuesta conversacional con streaming token-by-token."""
    cfg = get_config()
    prompt = f"""{SYSTEM_CONTEXT}

User: {user_message}
Assistant:"""

    try:
        resp = requests.post(
            f"{cfg['OLLAMA_URL']}/api/generate",
            json={"model": cfg["OLLAMA_MODEL"], "prompt": prompt,
                  "stream": True, "think": cfg.get("OLLAMA_THINK", False), "options": {"temperature": 0.7}},
            timeout=90, stream=True
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break
    except Exception:
        yield "Hola! Puedo ayudarte a desplegar servicios en Kubernetes. Dime que necesitas."


def classify_and_route(user_message: str) -> dict:
    """Clasifica intent y extrae parametros en una sola llamada a Ollama.

    Retorna:
        {"type": "chat"} si es conversacion, o
        {"type": "deploy", "intent": {...}} con los parametros extraidos.
    """
    cfg = get_config()
    prompt = f"""You are a classification and extraction engine. Analyze the user message and respond with ONLY a valid JSON object.

If the message is a DIRECT ORDER to CREATE/DEPLOY/LAUNCH a NEW service on Kubernetes, extract parameters.
If it is anything else (greetings, questions, help, troubleshooting, scaling, listing, etc.), classify as chat.

CRITICAL: Questions about deployment are NOT deploy orders. Only extract when explicitly commanded.

User message: "{user_message}"

For chat messages, return: {{"type": "chat"}}

For deploy orders, return: {{"type": "deploy", "service_name": "<name>", "replicas": <n>, "environment": "<staging|production>", "port": <n>, "has_database": <bool>, "db_type": "<postgresql|mysql|none>", "owner": "<team>", "description": "<brief>"}}

Rules for deploy extraction:
- service_name: lowercase, hyphens only, extract the CORE noun
- replicas: integer, default 1
- environment: "staging" or "production", default "staging"
- port: integer, default 8080
- has_database: true only if user mentions database/postgres/mysql/mongo/redis
- db_type: "postgresql", "mysql", or "none"
- owner: "backend-team" (APIs), "platform-team" (infra/nginx), "data-team" (data/ML), "frontend-team" (UI)
- description: max 8 words, same language as user

Output ONLY the JSON:"""

    defaults = {
        "service_name": "", "replicas": 1,
        "environment": "staging", "port": 8080,
        "has_database": False, "db_type": "none",
        "owner": "backend-team", "description": "servicio de demo"
    }

    try:
        resp = requests.post(
            f"{cfg['OLLAMA_URL']}/api/generate",
            json={"model": cfg["OLLAMA_MODEL"], "prompt": prompt,
                  "stream": False, "think": cfg.get("OLLAMA_THINK", False), "options": {"temperature": 0.0}},
            timeout=60
        )
        resp.raise_for_status()
        raw = resp.json()["response"].strip()

        for m in ["```json", "```"]:
            if m in raw:
                raw = raw.split(m)[1].split("```")[0].strip()
                break

        s, e = raw.find("{"), raw.rfind("}") + 1
        if s != -1 and e > s:
            raw = raw[s:e]

        parsed = json.loads(raw)

        if parsed.get("type") != "deploy":
            return {"type": "chat"}

        # Normalize deploy intent
        for k, v in defaults.items():
            parsed.setdefault(k, v)

        if not parsed.get("port") or parsed["port"] <= 0:
            parsed["port"] = 8080
        if not parsed.get("replicas") or parsed["replicas"] <= 0:
            parsed["replicas"] = 1
        if parsed.get("environment") not in ("staging", "production"):
            parsed["environment"] = "staging"

        parsed["service_name"] = (
            re.sub(r"[^a-z0-9-]", "-", parsed["service_name"].lower()).strip("-")
        )

        intent = {k: parsed[k] for k in defaults}
        return {"type": "deploy", "intent": intent}
    except Exception:
        return {"type": "chat"}
