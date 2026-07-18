#!/usr/bin/env python3
"""
KCD Peru 2026 — Demo Agent (CLI)
Flujo: Lenguaje natural → Ollama → Backstage → GitHub (PR + merge) → ArgoCD → kind
"""
import sys, json, subprocess, time, threading
from datetime import datetime
from pathlib import Path

# Agregar raiz del proyecto al path para importar core
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import (
    load_env, get_config,
    check_ollama, check_ollama_mlx, check_backstage, check_github, check_kubectl,
    classify_intent, chat_response, extract_intent, adjust_intent,
    get_missing_fields, apply_field,
    stream_chat_response, classify_and_route,
    step_backstage, wait_backstage_task,
    create_pr_via_github, merge_pull_request,
    argocd_sync, wait_for_pods, get_pods,
)

load_env()
cfg = get_config()

# ── Rich UI ──────────────────────────────────────────────────
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
        def rule(self, *a, **k): print("─"*50)
    console = _C()

# ── Helpers de UI ────────────────────────────────────────────
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

# ── Spinner inline para espera de LLM ───────────────────────
class InlineSpinner:
    """Spinner animado que se muestra en la misma linea y se borra al parar."""
    FRAMES = ["|", "/", "-", "\\"]

    def __init__(self, label="Agente"):
        self._stop = threading.Event()
        self._thread = None
        self._label = label

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        i = 0
        w = sys.stdout.write
        while not self._stop.is_set():
            frame = self.FRAMES[i % len(self.FRAMES)]
            w(f"\r  {self._label}: {frame} pensando...")
            sys.stdout.flush()
            i += 1
            self._stop.wait(0.1)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


# ── Wait con spinner ─────────────────────────────────────────
def wait_for_pods_with_spinner(intent: dict, timeout: int = 120) -> bool:
    name, ns = intent["service_name"], intent["environment"]
    if HAS_RICH:
        with Progress(SpinnerColumn(),
                      TextColumn(f"[dim]  Esperando pods en '{ns}'...[/dim]"),
                      console=console, transient=True) as p:
            p.add_task("")
            return wait_for_pods(intent, timeout)
    else:
        return wait_for_pods(intent, timeout)

def show_pods(intent: dict):
    ns = intent["environment"]
    pods = get_pods(ns)
    if not pods:
        return
    if HAS_RICH:
        t = Table(title=f"Pods en namespace '{ns}'",
                  header_style="bold cyan", border_style="dim")
        t.add_column("Nombre"); t.add_column("Ready")
        t.add_column("Status"); t.add_column("Age")
        for p in pods:
            color = "green" if p["status"] == "Running" else "yellow"
            t.add_row(p["name"], p["ready"], f"[{color}]{p['status']}[/{color}]", p["age"])
        console.print(t)
    else:
        print(f"\n  Pods en '{ns}':")
        for p in pods:
            print(f"    {p['name']}  {p['ready']}  {p['status']}  {p['age']}")

# ── Orquestador principal (optimizado: intent ya extraido) ───
def process_request_fast(user_input: str, intent: dict | None, bs_ok: bool, gh_ok: bool):
    """Procesa deploy con intent ya extraido por classify_and_route (1 sola llamada)."""
    if HAS_RICH:
        console.print()
        console.rule("[dim]nuevo deployment[/dim]")

    # 1. Intent ya fue extraido junto con la clasificacion
    h("Paso 1/5 — [bold]Ollama[/bold] analizo la intencion")
    if intent is None:
        intent = extract_intent(user_input)

    _process_deploy(user_input, intent, bs_ok, gh_ok)


# ── Orquestador principal (legacy — usado por web/mcp) ──────
def process_request(user_input: str, bs_ok: bool, gh_ok: bool):
    if HAS_RICH:
        console.print()
        console.rule("[dim]nuevo deployment[/dim]")

    # 1. Ollama
    h("Paso 1/5 — [bold]Ollama[/bold] analiza la intencion...")
    intent = extract_intent(user_input)

    _process_deploy(user_input, intent, bs_ok, gh_ok)


def _process_deploy(user_input: str, intent: dict, bs_ok: bool, gh_ok: bool):

    # Preguntar por campos requeridos faltantes
    missing = get_missing_fields(intent)
    for item in missing:
        try:
            answer = (Prompt.ask(
                f"\n[bold]{item['prompt']}[/bold]"
            ) if HAS_RICH else input(f"\n{item['prompt']}: ").strip())
        except (KeyboardInterrupt, EOFError):
            info("Deployment cancelado"); return
        if not answer.strip():
            info("Deployment cancelado — valor requerido no proporcionado"); return
        intent = apply_field(intent, item["field"], answer)

    # Verificar que service_name sea valido despues de aplicar
    if not intent.get("service_name"):
        warn("No se pudo determinar el nombre del servicio"); return

    # Mostrar intent y pedir confirmacion
    if HAS_RICH:
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column(style="dim", width=20)
        t.add_column(style="bold white")
        t.add_column(style="dim")
        t.add_row("Servicio",      intent["service_name"], "")
        t.add_row("Ambiente",      intent["environment"],  "(default)" if "staging" == intent["environment"] and intent["environment"] not in user_input.lower() else "")
        t.add_row("Replicas",      str(intent["replicas"]), "(default)" if intent["replicas"] == 1 and "1" not in user_input else "")
        t.add_row("Puerto",        str(intent["port"]),     "(default)" if intent["port"] == 8080 and "8080" not in user_input else "")
        t.add_row("Base de datos", intent["db_type"] if intent.get("has_database") else "No", "")
        t.add_row("Owner",         intent.get("owner","backend-team"), "(default)" if intent.get("owner") == "backend-team" and "team" not in user_input.lower() else "")
        console.print(Panel(t, border_style="cyan", title="[dim]intent extraido[/dim]"))
    else:
        print(f"  Servicio:      {intent['service_name']}")
        print(f"  Ambiente:      {intent['environment']}")
        print(f"  Replicas:      {intent['replicas']}")
        print(f"  Puerto:        {intent['port']}")
        print(f"  Base de datos: {intent['db_type'] if intent.get('has_database') else 'No'}")
        print(f"  Owner:         {intent.get('owner', 'backend-team')}")

    # Pedir confirmacion
    try:
        confirm = (Prompt.ask(
            "\n[bold]¿Confirmas el deployment?[/bold] [dim](si/no/cambiar valores)[/dim]",
            default="si"
        ) if HAS_RICH else input("\n¿Confirmas el deployment? (si/no/cambiar valores) [si]: ").strip() or "si")
    except (KeyboardInterrupt, EOFError):
        info("Deployment cancelado"); return

    confirm = confirm.strip().lower()
    if confirm in ("no", "n", "cancelar"):
        info("Deployment cancelado"); return

    if confirm not in ("si", "s", "yes", "y", ""):
        h("Ajustando parametros...")
        updated = adjust_intent(intent, confirm)
        if updated:
            intent = updated
            ok("Parametros actualizados")
            if HAS_RICH:
                t2 = Table(show_header=False, box=None, padding=(0, 2))
                t2.add_column(style="dim", width=20)
                t2.add_column(style="bold white")
                t2.add_row("Servicio",      intent["service_name"])
                t2.add_row("Ambiente",      intent["environment"])
                t2.add_row("Replicas",      str(intent["replicas"]))
                t2.add_row("Puerto",        str(intent["port"]))
                t2.add_row("Base de datos", intent["db_type"] if intent.get("has_database") else "No")
                t2.add_row("Owner",         intent.get("owner","backend-team"))
                console.print(Panel(t2, border_style="green", title="[dim]intent actualizado[/dim]"))
        else:
            warn("No se pudo ajustar — continuando con los valores originales")

    ok("Intent confirmado")

    # 2. Backstage genera manifest + crea PR
    h("Paso 2/5 — [bold]Backstage[/bold] genera manifest + crea PR en GitHub...")
    success, task_id = step_backstage(intent)
    if not success:
        warn("Backstage no pudo crear la task. El workshop requiere el IDP activo.")
        return
    ok("Task creada en Backstage")
    pr_url = wait_backstage_task(task_id)
    if not pr_url:
        warn("Backstage no devolvio la URL del PR. Verifica la task en el IDP.")
        return
    ok(f"PR creado via Backstage → {pr_url}")

    # 3. Auto-merge del PR
    if not gh_ok:
        h("Paso 3/5 — GitHub no configurado")
        info("Configura GITHUB_TOKEN en .env para el flujo GitOps")
    elif pr_url:
        h("Paso 3/5 — [bold]GitHub[/bold] merge del PR...")
        info(f"Auto-merge PR #{pr_url.rstrip('/').split('/')[-1]}...")
        merged = merge_pull_request(pr_url)
        if merged:
            ok(f"PR mergeado → manifest en main")
        else:
            warn("No se pudo mergear automaticamente — mergealo manualmente")

    # 4. ArgoCD sync
    if gh_ok:
        h("Paso 4/5 — [bold]ArgoCD[/bold] detecta el cambio y sincroniza...")
        synced = argocd_sync(intent["environment"])
        if synced:
            ok("ArgoCD sync iniciado")
        else:
            info("ArgoCD hara sync automatico en ~30s")
    else:
        h("Paso 4/5 — ArgoCD skip (sin GitHub)")

    # 5. Esperar pods
    if check_kubectl():
        h("Paso 5/5 — Esperando pods [bold]Running[/bold] en el cluster...")
        info("(30-60s la primera vez mientras Docker descarga la imagen)")
        ready = wait_for_pods_with_spinner(intent)
        if ready:
            ok("Pods Running! Deployment exitoso")
        else:
            info("Pods aun iniciando — verifica: kubectl get pods -n " + intent["environment"])
        show_pods(intent)

    name, ns = intent["service_name"], intent["environment"]
    if HAS_RICH:
        gh_line = (f"  [cyan]github.com/{cfg['GITHUB_REPO']}/tree/main/apps/{ns}[/cyan]\n\n"
                   if gh_ok else "")
        bs_line = (f"  [cyan]{cfg['BACKSTAGE_URL']}[/cyan]  → Catalog → {name}\n\n"
                   if bs_ok else "")
        console.print(Panel(
            f"[bold]GitHub:[/bold]\n\n{gh_line}"
            f"[bold]Backstage:[/bold]\n\n{bs_line}"
            f"[bold]Cluster:[/bold]\n\n"
            f"  [cyan]kubectl get pods -n {ns}[/cyan]\n"
            f"  [cyan]kubectl logs -l app={name} -n {ns}[/cyan]\n\n"
            f"[bold]Limpiar:[/bold]  [cyan]make clean-apps[/cyan]",
            title="[dim]recursos[/dim]", border_style="green"
        ))
        console.print(
            f"\n[bold green]✨ Demo completa![/bold green] "
            f"[dim]Lenguaje natural → Ollama → Backstage → "
            f"GitHub → ArgoCD → pods corriendo.[/dim]\n"
        )

# ── Main ─────────────────────────────────────────────────────
def main():
    if HAS_RICH:
        console.print(Panel.fit(
            "[bold blue]KCD Peru 2026 — Platform Engineering + AI[/bold blue]\n"
            "[dim]Lenguaje natural → Ollama → Backstage → GitHub → ArgoCD → kind[/dim]",
            border_style="blue", padding=(1, 2)
        ))
    else:
        print("=" * 65)
        print("KCD Peru 2026 — Platform Engineering + AI Demo")
        print("=" * 65)

    # Verificar servicios
    if HAS_RICH: console.print("\n[dim]Verificando servicios...[/dim]")

    if not check_ollama():
        err(f"Ollama no disponible o modelo '{cfg['OLLAMA_MODEL']}' no instalado")
        print(f"\n  Solucion:\n    ollama pull {cfg['OLLAMA_MODEL']}\n    ollama serve")
        sys.exit(1)
    ok(f"Ollama — {cfg['OLLAMA_MODEL']}")
    if not check_ollama_mlx():
        warn("Ollama sin aceleracion MLX — reinicia con: OLLAMA_NEW_ENGINE=1 ollama serve")

    if not check_kubectl():
        err("kubectl no conecta al cluster kind → make setup")
        sys.exit(1)
    ok("kubectl → kind-kcd-demo")

    bs_ok = check_backstage()
    gh_ok = check_github()

    if bs_ok:
        ok(f"Backstage → {cfg['BACKSTAGE_URL']}")
    else:
        err("Backstage no disponible. Inicia el IDP con: make backstage")
        sys.exit(1)

    if gh_ok:
        ok(f"GitHub GitOps → github.com/{cfg['GITHUB_REPO']}")
    else:
        if HAS_RICH:
            console.print(
                f"  [yellow]⚠️[/yellow]  [dim]GitHub no configurado — "
                f"agrega GITHUB_TOKEN y GITHUB_REPO en .env[/dim]"
            )
        else:
            warn("GitHub no configurado")

    if HAS_RICH:
        mode = []
        if bs_ok: mode.append("Backstage")
        if gh_ok: mode.append("GitHub GitOps")
        if not mode: mode.append("sin flujo GitOps")
        console.print(
            f"  [bold]Modo activo:[/bold] [green]{' + '.join(mode)}[/green]\n"
        )
        console.rule()
        console.print("[bold]Ejemplos:[/bold]")
        for ex in [
            "Despliega una API de usuarios con PostgreSQL en staging con 3 replicas",
            "Necesito un microservicio de pagos en produccion con 2 replicas",
            "Crea un servicio de notificaciones en staging",
        ]:
            console.print(f"  [dim]→ {ex}[/dim]")
        console.print("[dim]Comandos: 'status' · 'salir'[/dim]")
        console.rule()

    while True:
        try:
            user_input = (Prompt.ask("\n[bold green]Tu[/bold green]") if HAS_RICH
                          else input("\nTu: ").strip())
        except (KeyboardInterrupt, EOFError):
            print("\nHasta luego!"); break

        user_input = user_input.strip()
        if not user_input: continue
        if user_input.lower() in ("salir", "exit", "q", "quit"):
            print("Hasta luego!"); break
        if user_input.lower() == "status":
            subprocess.run(["kubectl", "get", "pods", "--all-namespaces"]); continue

        t_start = datetime.now()
        if HAS_RICH:
            console.print(f"  [dim]{t_start:%H:%M:%S} → enviado[/dim]")
        else:
            print(f"  {t_start:%H:%M:%S} → enviado")

        spinner = InlineSpinner()
        spinner.start()
        result = classify_and_route(user_input)
        t_first = None
        if result["type"] == "deploy":
            spinner.stop()
            process_request_fast(user_input, result.get("intent"), bs_ok, gh_ok)
        else:
            for token in stream_chat_response(user_input):
                if t_first is None:
                    t_first = datetime.now()
                    spinner.stop()
                    if HAS_RICH:
                        console.print(f"\n[bold blue]Agente:[/bold blue] ", end="")
                    else:
                        print(f"\nAgente: ", end="")
                print(token, end="", flush=True)
            if t_first is None:
                spinner.stop()
            print()

        t_end = datetime.now()
        elapsed = (t_end - t_start).total_seconds()
        if HAS_RICH:
            ttft = f"  TTFT: {(t_first - t_start).total_seconds():.1f}s |" if t_first else ""
            console.print(f"  [dim]{t_end:%H:%M:%S} → respuesta ({ttft} total: {elapsed:.1f}s)[/dim]")
        else:
            print(f"  {t_end:%H:%M:%S} → respuesta (total: {elapsed:.1f}s)")

if __name__ == "__main__":
    main()
