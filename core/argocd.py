"""Sincronizacion con ArgoCD."""
import subprocess
import requests
from .config import get_config


def _argocd_token() -> str:
    cfg = get_config()
    if not cfg["ARGOCD_PASSWORD"]:
        return ""
    try:
        import urllib3
        urllib3.disable_warnings()
    except ImportError:
        pass
    try:
        r = requests.post(
            f"https://{cfg['ARGOCD_SERVER']}/api/v1/session",
            json={"username": "admin", "password": cfg["ARGOCD_PASSWORD"]},
            verify=False, timeout=10
        )
        if r.status_code == 200:
            return r.json().get("token", "")
    except Exception:
        pass
    return ""


def argocd_sync(env: str) -> bool:
    """Fuerza sync de ArgoCD. Intenta CLI primero, luego API REST."""
    cfg = get_config()
    app_name = f"{env}-apps"

    try:
        import urllib3
        urllib3.disable_warnings()
    except ImportError:
        pass

    # Intentar via CLI
    try:
        token = _argocd_token()
        if token:
            r = subprocess.run(
                ["argocd", "app", "sync", app_name,
                 "--server", cfg["ARGOCD_SERVER"],
                 "--auth-token", token,
                 "--insecure", "--grpc-web",
                 "--timeout", "30"],
                capture_output=True, text=True, timeout=40
            )
            if r.returncode == 0:
                return True
    except (FileNotFoundError, Exception):
        pass

    # Fallback: API REST
    token = _argocd_token()
    if not token:
        return False
    try:
        r = requests.post(
            f"https://{cfg['ARGOCD_SERVER']}/api/v1/applications/{app_name}/sync",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={}, verify=False, timeout=30
        )
        return r.status_code in (200, 201)
    except Exception:
        return False
