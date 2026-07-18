"""Carga de .env y configuracion global."""
import os
from pathlib import Path


def load_env(base_path: Path | None = None):
    """Carga variables de .env al entorno si no estan definidas."""
    if base_path is None:
        base_path = Path(__file__).parent.parent
    env_file = base_path / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_config() -> dict:
    """Retorna la configuracion actual como dict."""
    return {
        "OLLAMA_URL": os.getenv("OLLAMA_URL", "http://localhost:11434"),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "OLLAMA_THINK": os.getenv("OLLAMA_THINK", "false").lower() in ("true", "1", "yes"),
        "BACKSTAGE_URL": os.getenv("BACKSTAGE_URL", "http://localhost:7007"),
        "BACKSTAGE_TOKEN": os.getenv("BACKSTAGE_TOKEN", ""),
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
        "GITHUB_REPO": os.getenv("GITHUB_REPO", ""),
        "ARGOCD_SERVER": os.getenv("ARGOCD_SERVER", "localhost:8080"),
        "ARGOCD_PASSWORD": os.getenv("ARGOCD_PASSWORD", ""),
    }
