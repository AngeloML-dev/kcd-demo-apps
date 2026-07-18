"""Health checks para los servicios externos."""
import subprocess
import requests
from .config import get_config


def _bs_headers() -> dict:
    cfg = get_config()
    h = {"Content-Type": "application/json"}
    if cfg["BACKSTAGE_TOKEN"]:
        h["Authorization"] = f"Bearer {cfg['BACKSTAGE_TOKEN']}"
    return h


def check_ollama() -> bool:
    cfg = get_config()
    try:
        r = requests.get(f"{cfg['OLLAMA_URL']}/api/tags", timeout=5)
        return any(cfg["OLLAMA_MODEL"].split(":")[0] in m["name"]
                   for m in r.json().get("models", []))
    except Exception:
        return False


def check_ollama_mlx() -> bool:
    """Verifica si Ollama tiene un modelo cargado con procesador GPU (MLX/Metal)."""
    cfg = get_config()
    try:
        r = requests.get(f"{cfg['OLLAMA_URL']}/api/ps", timeout=5)
        models = r.json().get("models", [])
        if not models:
            return True  # No model loaded yet, can't tell
        for m in models:
            proc = m.get("size_vram", 0)
            total = m.get("size", 1)
            if proc / total < 0.5:
                return False  # Less than 50% on GPU
        return True
    except Exception:
        return True  # Can't check, assume OK


def check_backstage() -> bool:
    cfg = get_config()
    try:
        r = requests.get(f"{cfg['BACKSTAGE_URL']}/api/catalog/entities",
                         headers=_bs_headers(), timeout=5)
        return r.status_code in (200, 401, 403, 404)
    except Exception:
        return False


def check_github() -> bool:
    cfg = get_config()
    token, repo = cfg["GITHUB_TOKEN"], cfg["GITHUB_REPO"]
    if not token or not repo:
        return False
    if token.startswith("ghp_xxx"):
        return False
    if repo.startswith("tu-usuario"):
        return False
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}",
            headers={"Authorization": f"token {token}",
                     "Accept": "application/vnd.github.v3+json"},
            timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def check_argocd() -> bool:
    r = subprocess.run(
        ["kubectl", "get", "svc", "argocd-server", "-n", "argocd",
         "--request-timeout=5s"],
        capture_output=True, text=True)
    return r.returncode == 0


def check_kubectl() -> bool:
    r = subprocess.run(
        ["kubectl", "cluster-info", "--request-timeout=5s"],
        capture_output=True, text=True)
    return r.returncode == 0
