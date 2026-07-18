#!/usr/bin/env python3
"""
KCD Peru 2026 — Portal Web con SSE
Flujo: Ollama → Backstage (genera YAML + PR) → GitHub (merge) → ArgoCD → pods
"""
import json, time, sys
from pathlib import Path

# Agregar raiz del proyecto al path para importar core
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import (
    load_env, get_config,
    check_ollama, check_backstage, check_github, check_kubectl, check_argocd,
    classify_intent, chat_response, extract_intent,
    get_missing_fields,
    step_backstage, wait_backstage_task,
    create_pr_via_github, merge_pull_request,
    argocd_sync, wait_for_pods, get_pods,
)

load_env()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="KCD Peru 2026 — Demo Portal")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "app" / "static"), name="static")


# ── Helpers ───────────────────────────────────────────────────
def sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}

# ── Pipeline SSE ──────────────────────────────────────────────
async def pipeline_generator(prompt: str):
    start_time = time.time()

    ollama_ok = check_ollama()
    bs_ok = check_backstage()
    gh_ok = check_github()
    argo_ok = check_argocd()
    k8s_ok = check_kubectl()

    yield sse("services", {
        "ollama": ollama_ok, "backstage": bs_ok,
        "github": gh_ok, "argocd": argo_ok, "kubectl": k8s_ok
    })

    if not ollama_ok:
        yield sse("step_start", {"id": "ollama", "msg": "Conectando a Ollama..."})
        yield sse("step_warn", {"id": "ollama", "msg": "Ollama no disponible"})
        return

    # Paso 1 — Ollama clasifica + extrae intent
    yield sse("step_start", {"id": "ollama", "msg": "Ollama analiza la intencion..."})
    intent_type = classify_intent(prompt)

    if intent_type == "chat":
        response = chat_response(prompt)
        yield sse("step_done", {"id": "ollama"})
        yield sse("chat", {"message": response})
        return

    intent = extract_intent(prompt)

    # Verificar campos faltantes
    missing = get_missing_fields(intent)
    if missing:
        yield sse("step_done", {"id": "ollama"})
        yield sse("missing_fields", {
            "intent": intent,
            "fields": missing,
        })
        return

    yield sse("intent", intent)
    yield sse("step_done", {"id": "ollama"})
    # Pipeline se detiene aqui — el frontend muestra confirmacion
    # y re-envia el intent via POST /api/deploy para ejecutar pasos 2-5

async def pipeline_from_intent(intent: dict):
    """Pipeline que arranca desde un intent ya confirmado (pasos 2-5)."""
    start_time = time.time()

    bs_ok = check_backstage()
    gh_ok = check_github()
    argo_ok = check_argocd()
    k8s_ok = check_kubectl()

    yield sse("services", {
        "ollama": True, "backstage": bs_ok,
        "github": gh_ok, "argocd": argo_ok, "kubectl": k8s_ok
    })

    yield sse("intent", intent)
    yield sse("step_done", {"id": "ollama"})

    if not bs_ok:
        yield sse("step_warn", {"id": "backstage", "msg": "Backstage es requerido para este workshop"})
        return

    # Paso 2 — Backstage (genera YAML + crea PR)
    pr_url = ""
    yield sse("step_start", {"id": "backstage", "msg": "Backstage genera manifest + crea PR..."})
    success, task_id = step_backstage(intent)
    if not success:
        yield sse("step_warn", {"id": "backstage", "msg": "Backstage no pudo crear la task"})
        return
    pr_url = wait_backstage_task(task_id)
    if not pr_url:
        yield sse("step_warn", {"id": "backstage", "msg": "Backstage completo sin PR URL"})
        return
    yield sse("step_done", {"id": "backstage", "pr_url": pr_url})

    # Paso 3 — Auto-merge PR
    if pr_url and gh_ok:
        yield sse("step_start", {"id": "github", "msg": "Merge del PR en GitHub..."})
        merged = merge_pull_request(pr_url)
        if merged:
            yield sse("step_done", {"id": "github", "pr_url": pr_url})
        else:
            yield sse("step_warn", {"id": "github", "msg": "Auto-merge fallo"})
    elif not pr_url:
        yield sse("step_skip", {"id": "github", "msg": "Sin PR que mergear"})
    else:
        yield sse("step_skip", {"id": "github", "msg": "GitHub no configurado"})

    # Paso 4 — ArgoCD sync
    if gh_ok and (pr_url or argo_ok):
        yield sse("step_start", {"id": "argocd", "msg": "ArgoCD sincronizando..."})
        synced = argocd_sync(intent["environment"])
        if synced:
            yield sse("step_done", {"id": "argocd"})
        else:
            yield sse("step_warn", {"id": "argocd", "msg": "ArgoCD sync manual — polling en ~30s"})
    else:
        yield sse("step_skip", {"id": "argocd", "msg": "ArgoCD skip"})

    # Paso 5 — Pods
    if k8s_ok:
        yield sse("step_start", {"id": "pods", "msg": "Esperando pods Running..."})
        ready = wait_for_pods(intent)
        pods = get_pods(intent["environment"])
        if ready:
            yield sse("step_done", {"id": "pods", "pods": pods})
        else:
            yield sse("step_warn", {"id": "pods", "msg": "Pods aun iniciando", "pods": pods})
    else:
        yield sse("step_skip", {"id": "pods", "msg": "kubectl no disponible"})

    elapsed = round(time.time() - start_time, 1)
    yield sse("done", {
        "service": intent["service_name"],
        "env": intent["environment"],
        "replicas": intent["replicas"],
        "elapsed": elapsed,
        "pr_url": pr_url
    })


# ── Endpoints ─────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    html_path = Path(__file__).parent / "app" / "index.html"
    return HTMLResponse(html_path.read_text())

@app.get("/api/deploy")
async def deploy(prompt: str):
    return EventSourceResponse(pipeline_generator(prompt))

@app.post("/api/deploy")
async def deploy_with_intent(request: Request):
    """Recibe un intent completo (tras llenar campos faltantes) y ejecuta el pipeline."""
    body = await request.json()
    intent = body.get("intent", {})
    if not intent.get("service_name"):
        return JSONResponse({"error": "service_name es requerido"}, status_code=400)
    return EventSourceResponse(pipeline_from_intent(intent))

@app.get("/api/status")
async def status():
    cfg = get_config()
    return JSONResponse({
        "ollama": check_ollama(),
        "backstage": check_backstage(),
        "github": check_github(),
        "argocd": check_argocd(),
        "kubectl": check_kubectl(),
        "model": cfg["OLLAMA_MODEL"],
    })

@app.get("/api/pods/{namespace}")
async def pods(namespace: str):
    return JSONResponse(get_pods(namespace))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
