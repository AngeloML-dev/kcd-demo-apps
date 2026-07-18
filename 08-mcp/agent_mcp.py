#!/usr/bin/env python3
"""
KCD Peru 2026 — Agente con MCP (Kubernetes + GitHub)
Usa qwen3.5:35b-a3b con function calling nativo para interactuar
con el cluster y GitHub via MCP servers.

Flujo: Ollama → Backstage → GitHub MCP → ArgoCD → Kubernetes MCP
"""
import sys, json, asyncio, re, signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import (
    load_env, get_config,
    check_ollama, check_backstage, check_kubectl,
    extract_intent, classify_intent,
    step_backstage, wait_backstage_task,
    generate_manifest,
    argocd_sync,
)
from core.intent import get_missing_fields, apply_field

from mcp_tools import MCPToolManager

import requests

load_env()

# ── Config ──────────────────────────────────────────────────
MCP_MODEL = "qwen3.5:35b-a3b"
OLLAMA_TIMEOUT = 300

# ── Rich UI ─────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt
    from rich.progress import Progress, SpinnerColumn, TextColumn
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    class _C:
        def print(self, *a, **k): print(*a)
        def rule(self, *a, **k): print("─" * 50)
    console = _C()

def h(msg):
    if HAS_RICH: console.print(f"\n[bold]{msg}[/bold]")
    else: print(f"\n>> {msg}")

def ok(msg):
    if HAS_RICH: console.print(f"  [green]✔[/green]  {msg}")
    else: print(f"  [OK] {msg}")

def info(msg):
    if HAS_RICH: console.print(f"  [cyan]ℹ[/cyan]  [dim]{msg}[/dim]")
    else: print(f"  [i] {msg}")

def warn(msg):
    if HAS_RICH: console.print(f"  [yellow]⚠️[/yellow]  {msg}")
    else: print(f"  [!] {msg}")

def err(msg):
    if HAS_RICH: console.print(f"  [red]✘[/red]  [bold red]{msg}[/bold red]")
    else: print(f"  [ERR] {msg}")

def show_tool_call(name: str, args: dict):
    if HAS_RICH:
        args_str = json.dumps(args, indent=2, ensure_ascii=False) if args else "{}"
        console.print(f"\n  [bold magenta]⚡ tool:[/bold magenta] [cyan]{name}[/cyan]")
        if args and len(args_str) < 200:
            console.print(f"  [dim]{args_str}[/dim]")
    else:
        print(f"\n  > tool: {name}({args})")

def show_tool_result(result: str):
    if HAS_RICH:
        display = result[:500] + "..." if len(result) > 500 else result
        console.print(f"  [dim green]← {display}[/dim green]")
    else:
        display = result[:300] + "..." if len(result) > 300 else result
        print(f"  <- {display}")


# ── Classify con soporte de acciones de K8s ─────────────────
def classify_intent_mcp(user_message: str) -> str:
    """Clasifica como 'deploy', 'k8s_action' o 'chat'.
    k8s_action = reiniciar, escalar, borrar, ver logs de un recurso existente.
    deploy = crear algo nuevo.
    chat = todo lo demas.
    """
    cfg = get_config()
    prompt = f"""Task: classify this message into exactly ONE category. Answer with ONE word ONLY. No explanation.

deploy = the user gives a DIRECT ORDER to CREATE, DEPLOY, or LAUNCH a NEW service, application, or workload on Kubernetes RIGHT NOW. Must be an imperative command to create something new.
k8s_action = the user gives a DIRECT ORDER to perform a MUTATING action on an EXISTING specific Kubernetes resource: RESTART a specific pod/deployment, SCALE a specific deployment to N replicas, DELETE a specific resource, ROLLBACK a specific deployment, PORT-FORWARD to a specific service. The user must name or identify the specific resource.
chat = EVERYTHING else: greetings, questions (even about deploying), listing/viewing resources, checking status, troubleshooting, concepts, help, any message with "?".

Examples:
"despliega un servicio de pagos en staging" → deploy
"crea una API de usuarios con postgres" → deploy
"reinicia el pod de pagos en staging" → k8s_action
"escala el deployment de nginx a 5 replicas" → k8s_action
"borra el pod api-usuarios-xyz en production" → k8s_action
"como despliego un servicio?" → chat
"que pods hay en staging?" → chat
"hola" → chat
"muestra los logs del pod nginx" → chat
"que es un deployment?" → chat
"puedes reiniciar pods?" → chat

When in doubt, answer "chat".

Message: "{user_message}"
Answer:"""

    try:
        resp = requests.post(
            f"{cfg['OLLAMA_URL']}/api/generate",
            json={"model": cfg["OLLAMA_MODEL"], "prompt": prompt,
                  "stream": False, "options": {"temperature": 0.0}},
            timeout=15
        )
        resp.raise_for_status()
        raw = resp.json()["response"].strip().lower()
        if raw.startswith("deploy"):
            return "deploy"
        if raw.startswith("k8s"):
            return "k8s_action"
        return "chat"
    except Exception:
        return "chat"


# ── Ollama con function calling ─────────────────────────────
def ollama_chat(messages: list, tools: list | None = None) -> dict:
    cfg = get_config()
    payload = {
        "model": MCP_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    if tools:
        payload["tools"] = tools

    resp = requests.post(
        f"{cfg['OLLAMA_URL']}/api/chat",
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def warmup_model():
    cfg = get_config()
    if HAS_RICH:
        with Progress(SpinnerColumn(),
                      TextColumn(f"[dim]  Cargando {MCP_MODEL} en GPU (primera vez toma ~30s)...[/dim]"),
                      console=console, transient=True) as p:
            p.add_task("")
            try:
                requests.post(
                    f"{cfg['OLLAMA_URL']}/api/chat",
                    json={"model": MCP_MODEL, "messages": [{"role": "user", "content": "hi"}],
                          "stream": False, "options": {"num_predict": 1}},
                    timeout=OLLAMA_TIMEOUT,
                )
            except Exception:
                pass
    else:
        print("  Cargando modelo...")
        try:
            requests.post(
                f"{cfg['OLLAMA_URL']}/api/chat",
                json={"model": MCP_MODEL, "messages": [{"role": "user", "content": "hi"}],
                      "stream": False, "options": {"num_predict": 1}},
                timeout=OLLAMA_TIMEOUT,
            )
        except Exception:
            pass


# ── Tool calling loop ───────────────────────────────────────
async def agent_loop(user_message: str, mcp: MCPToolManager,
                     system_prompt: str, max_iterations: int = 10) -> str:
    tools = mcp.get_tools_for_ollama()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    for i in range(max_iterations):
        if HAS_RICH and i == 0:
            with Progress(SpinnerColumn(),
                          TextColumn("[dim]  Pensando...[/dim]"),
                          console=console, transient=True) as p:
                p.add_task("")
                response = ollama_chat(messages, tools=tools if tools else None)
        else:
            response = ollama_chat(messages, tools=tools if tools else None)

        msg = response.get("message", {})

        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            return msg.get("content", "")

        messages.append(msg)

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})

            show_tool_call(name, args)
            result = await mcp.call_tool(name, args)
            show_tool_result(result)

            messages.append({
                "role": "tool",
                "content": result,
            })

    return "Se alcanzo el limite de iteraciones del agente."


# ── K8s action via MCP ──────────────────────────────────────
async def process_k8s_action(user_input: str, mcp: MCPToolManager):
    """Ejecuta acciones sobre recursos existentes de Kubernetes via MCP."""
    system_prompt = """Eres un asistente de Kubernetes que ejecuta acciones sobre recursos EXISTENTES en el cluster.

IMPORTANTE: Usa las tools de Kubernetes disponibles para ejecutar la accion solicitada. NO inventes resultados.

Acciones que puedes ejecutar:
- Reiniciar pods/deployments (delete pod o rollout restart)
- Escalar deployments (scale)
- Ver logs de pods
- Describir recursos (describe)
- Ver eventos del namespace

Flujo:
1. Identifica el recurso y namespace del mensaje del usuario
2. Ejecuta la accion con la tool correspondiente
3. Reporta el resultado real

Responde en espanol, breve y directo. Confirma lo que hiciste con datos reales del cluster."""

    result = await agent_loop(user_input, mcp, system_prompt, max_iterations=5)

    if HAS_RICH:
        console.print(f"\n[bold blue]Agente:[/bold blue] {result}")
    else:
        print(f"\nAgente: {result}")


# ── Deploy pipeline con MCP ─────────────────────────────────
async def process_deploy(user_input: str, mcp: MCPToolManager,
                         bs_ok: bool, gh_ok: bool):
    cfg = get_config()

    if HAS_RICH:
        console.print()
        console.rule("[dim]nuevo deployment[/dim]")

    # 1. Ollama parsea intent
    h("Paso 1/5 — [bold]Ollama[/bold] analiza la intencion...")
    intent = extract_intent(user_input)

    # Preguntar por campos requeridos faltantes
    missing = get_missing_fields(intent)
    for item in missing:
        try:
            answer = (Prompt.ask(
                f"\n[bold]{item['prompt']}[/bold]"
            ) if HAS_RICH else input(f"\n{item['prompt']}: ").strip())
        except (KeyboardInterrupt, EOFError):
            info("Cancelado"); return
        if not answer.strip():
            info("Cancelado — valor requerido no proporcionado"); return
        intent = apply_field(intent, item["field"], answer)

    # Verificar que service_name sea valido despues de aplicar
    if not intent.get("service_name"):
        warn("No se pudo determinar el nombre del servicio"); return

    if HAS_RICH:
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column(style="dim", width=20)
        t.add_column(style="bold white")
        t.add_row("Servicio",      intent["service_name"])
        t.add_row("Ambiente",      intent["environment"])
        t.add_row("Replicas",      str(intent["replicas"]))
        t.add_row("Puerto",        str(intent["port"]))
        t.add_row("Base de datos", intent["db_type"] if intent.get("has_database") else "No")
        t.add_row("Owner",         intent.get("owner", "backend-team"))
        console.print(Panel(t, border_style="cyan", title="[dim]intent extraido[/dim]"))

    try:
        confirm = (Prompt.ask(
            "\n[bold]¿Confirmas el deployment?[/bold] [dim](si/no)[/dim]",
            default="si"
        ) if HAS_RICH else input("\n¿Confirmas? (si/no) [si]: ").strip() or "si")
    except (KeyboardInterrupt, EOFError):
        info("Cancelado"); return

    if confirm.strip().lower() in ("no", "n"):
        info("Cancelado"); return

    ok("Intent confirmado")
    name = intent["service_name"]
    env = intent["environment"]
    owner, repo = cfg["GITHUB_REPO"].split("/", 1) if "/" in cfg["GITHUB_REPO"] else ("", "")

    # 2. Backstage genera manifest + crea PR
    pr_url = ""
    if bs_ok:
        h("Paso 2/5 — [bold]Backstage[/bold] genera manifest + crea PR...")
        success, task_id = step_backstage(intent)
        if success:
            ok("Task creada en Backstage")
            pr_url = wait_backstage_task(task_id)
            if pr_url:
                ok(f"PR creado via Backstage → {pr_url}")

    if not pr_url and gh_ok:
        if bs_ok:
            info("Backstage no devolvio PR URL — creando via GitHub MCP...")
        else:
            h("Paso 2/5 — Generando manifest + PR via [bold]GitHub MCP[/bold]...")

        manifest = generate_manifest(intent)
        pr_prompt = f"""Necesito crear un deployment en GitHub. Haz lo siguiente en orden:

1. Crea un branch llamado "deploy/{name}-{env}" desde main en el repo {owner}/{repo}
2. Sube este archivo YAML en la ruta "apps/{env}/{name}.yaml" en ese branch:

```yaml
{manifest}
```

3. Crea un Pull Request del branch "deploy/{name}-{env}" hacia main con:
   - Titulo: "feat: deploy {name} to {env}"
   - Body: "Deployment generado por KCD Demo Agent - Servicio: {name}, Ambiente: {env}, Replicas: {intent['replicas']}"

Ejecuta los pasos usando las tools disponibles."""

        result = await agent_loop(
            pr_prompt, mcp,
            system_prompt="Eres un asistente que ejecuta operaciones en GitHub. Usa las tools disponibles. Se breve en tus respuestas.",
            max_iterations=6,
        )
        if HAS_RICH:
            console.print(f"\n  [blue]{result}[/blue]")

        if "pull" in result.lower() and ("http" in result or "#" in result):
            urls = re.findall(r'https://github\.com/[^\s\)]+/pull/\d+', result)
            if urls:
                pr_url = urls[0]
                ok(f"PR creado via GitHub MCP → {pr_url}")

    elif not pr_url and not gh_ok:
        h("Paso 2/5 — Sin Backstage ni GitHub configurado")
        warn("Configura GITHUB_TOKEN en .env o inicia Backstage")

    # 3. Merge PR via GitHub MCP
    if pr_url and gh_ok:
        h("Paso 3/5 — [bold]GitHub MCP[/bold] merge del PR...")
        pr_number = pr_url.rstrip("/").split("/")[-1]
        merge_result = await agent_loop(
            f"Mergea el Pull Request #{pr_number} en el repo {owner}/{repo} usando squash merge.",
            mcp,
            system_prompt="Eres un asistente que ejecuta operaciones en GitHub. Usa las tools disponibles. Se breve.",
            max_iterations=3,
        )
        if "merge" in merge_result.lower() or "merged" in merge_result.lower():
            ok("PR mergeado via MCP")
        else:
            warn(f"Resultado del merge: {merge_result[:100]}")
    elif not gh_ok:
        h("Paso 3/5 — GitHub no configurado")

    # 4. ArgoCD sync
    if gh_ok:
        h("Paso 4/5 — [bold]ArgoCD[/bold] sincroniza...")
        synced = argocd_sync(env)
        if synced:
            ok("ArgoCD sync iniciado")
        else:
            info("ArgoCD hara sync automatico en ~30s")
    else:
        h("Paso 4/5 — ArgoCD skip (sin GitHub)")

    # 5. Verificar pods via Kubernetes MCP
    if check_kubectl():
        h("Paso 5/5 — [bold]Kubernetes MCP[/bold] verifica pods...")
        pods_result = await agent_loop(
            f"Lista los pods en el namespace '{env}'. Dime cuantos hay y su estado.",
            mcp,
            system_prompt="Eres un asistente de Kubernetes. Usa las tools para consultar el cluster. Responde en espanol, breve y directo.",
            max_iterations=3,
        )
        if HAS_RICH:
            console.print(f"\n  [blue]{pods_result}[/blue]")

    if HAS_RICH:
        console.print(Panel(
            f"[bold]Cluster:[/bold]\n\n"
            f"  [cyan]kubectl get pods -n {env}[/cyan]\n"
            f"  [cyan]kubectl logs -l app={name} -n {env}[/cyan]\n\n"
            f"[bold]Limpiar:[/bold]  [cyan]make clean-apps[/cyan]\n\n"
            f"[dim]Ahora puedes preguntar sobre el estado del cluster.[/dim]",
            title="[dim]recursos[/dim]", border_style="green"
        ))


# ── Chat con MCP tools ──────────────────────────────────────
async def process_chat(user_input: str, mcp: MCPToolManager):
    system_prompt = """Eres un experto en Kubernetes y Platform Engineering. Respondes en espanol, de forma clara y concisa.

Tienes acceso a tools de Kubernetes y GitHub. Decide si necesitas usarlas:

USA tools cuando el usuario pida informacion REAL del cluster o repo:
- "que pods hay en staging?" → usa tool de Kubernetes para listar pods
- "muestra los logs de nginx" → usa tool de Kubernetes para ver logs
- "que PRs hay abiertos?" → usa tool de GitHub para listar PRs
- "describe el deployment X" → usa tool de Kubernetes para describe

NO uses tools para:
- Saludos → responde directamente con un saludo breve
- Preguntas conceptuales ("que es un pod?") → responde con tu conocimiento
- Troubleshooting general → da pasos y comandos kubectl
- Preguntas sobre este portal → explica el flujo: lenguaje natural → Ollama → Backstage → GitHub → ArgoCD → pods

Maximo 4-5 oraciones por respuesta. Si usas una tool, reporta los resultados reales."""

    result = await agent_loop(user_input, mcp, system_prompt, max_iterations=5)

    if HAS_RICH:
        console.print(f"\n[bold blue]Agente:[/bold blue] {result}")
    else:
        print(f"\nAgente: {result}")


# ── Main ────────────────────────────────────────────────────
async def async_main():
    cfg = get_config()
    mcp = MCPToolManager()

    if HAS_RICH:
        console.print(Panel.fit(
            "[bold blue]KCD Peru 2026 — Agente con MCP[/bold blue]\n"
            f"[dim]qwen3.5:35b-a3b + Kubernetes MCP + GitHub MCP[/dim]\n"
            "[dim]Ollama → Backstage → GitHub → ArgoCD → kubectl[/dim]",
            border_style="blue", padding=(1, 2)
        ))
    else:
        print("=" * 65)
        print("KCD Peru 2026 — Agente con MCP")
        print("=" * 65)

    # ── Verificar servicios ──────────────────────────────────
    if HAS_RICH: console.print("\n[dim]Verificando servicios...[/dim]")

    try:
        r = requests.get(f"{cfg['OLLAMA_URL']}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        if not any(MCP_MODEL.split(":")[0] in m for m in models):
            err(f"Modelo '{MCP_MODEL}' no encontrado en Ollama")
            print(f"\n  Solucion: ollama pull {MCP_MODEL}")
            sys.exit(1)
        ok(f"Ollama — {MCP_MODEL}")
    except requests.exceptions.ConnectionError:
        err("Ollama no disponible")
        print(f"\n  Solucion: ollama serve && ollama pull {MCP_MODEL}")
        sys.exit(1)

    if not check_kubectl():
        err("kubectl no conecta al cluster → make setup")
        sys.exit(1)
    ok("kubectl → kind-kcd-demo")

    bs_ok = check_backstage()
    if bs_ok:
        ok(f"Backstage → {cfg['BACKSTAGE_URL']}")
    else:
        warn("Backstage offline → make backstage")

    # ── Pre-cargar modelo en GPU ─────────────────────────────
    warmup_model()
    ok(f"{MCP_MODEL} cargado en GPU")

    # ── Conectar MCP servers ─────────────────────────────────
    if HAS_RICH:
        console.print("\n[dim]Conectando MCP servers...[/dim]")

    k8s_ok = await mcp.connect_kubernetes()
    if k8s_ok:
        ok(f"Kubernetes MCP → {len(mcp._k8s_tools)} tools disponibles")
    else:
        warn("Kubernetes MCP no disponible — verificar: npx mcp-server-kubernetes")

    gh_ok = await mcp.connect_github()
    if gh_ok:
        ok(f"GitHub MCP → {len(mcp._gh_tools)} tools disponibles")
    else:
        warn("GitHub MCP no disponible — verificar GITHUB_TOKEN en .env")

    filtered_tools = mcp.get_tools_for_ollama()
    all_tools = mcp.get_all_tools()
    if HAS_RICH and all_tools:
        console.print(f"\n  [bold]Tools MCP:[/bold] [green]{len(filtered_tools)}[/green] activas (de {len(all_tools)} totales)")
        for t in filtered_tools[:10]:
            console.print(f"    [dim]→ {t['function']['name']}[/dim]")
        if len(filtered_tools) > 10:
            console.print(f"    [dim]... y {len(filtered_tools) - 10} mas[/dim]")

    if HAS_RICH:
        console.print()
        console.rule()
        console.print("[bold]Ejemplos:[/bold]")
        for ex in [
            "Despliega una API de usuarios con PostgreSQL en staging con 3 replicas",
            "¿Que pods hay corriendo en staging?",
            "Reinicia el pod api-usuarios en staging",
            "¿Que PRs hay abiertos en el repo?",
        ]:
            console.print(f"  [dim]→ {ex}[/dim]")
        console.print("[dim]Comandos: 'salir'[/dim]")
        console.rule()

    # ── Loop principal ───────────────────────────────────────
    try:
        while True:
            try:
                user_input = (Prompt.ask("\n[bold green]Tu[/bold green]") if HAS_RICH
                              else input("\nTu: ").strip())
            except (KeyboardInterrupt, EOFError):
                print("\nHasta luego!"); break

            user_input = user_input.strip()
            if not user_input:
                continue
            if user_input.lower() in ("salir", "exit", "q", "quit"):
                print("Hasta luego!"); break

            try:
                intent_type = classify_intent_mcp(user_input)
                if intent_type == "deploy":
                    await process_deploy(user_input, mcp, bs_ok, gh_ok)
                elif intent_type == "k8s_action":
                    await process_k8s_action(user_input, mcp)
                else:
                    await process_chat(user_input, mcp)
            except KeyboardInterrupt:
                warn("Operacion cancelada")
                continue
            except Exception as e:
                err(f"Error: {e}")
                continue
    finally:
        # Cerrar MCP limpiamente
        info("Cerrando MCP servers...")
        await mcp.close()


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nHasta luego!")


if __name__ == "__main__":
    main()
