"""Helpers compartidos: headers, utilidades de GitHub."""
from .config import get_config


def bs_headers() -> dict:
    cfg = get_config()
    h = {"Content-Type": "application/json"}
    if cfg["BACKSTAGE_TOKEN"]:
        h["Authorization"] = f"Bearer {cfg['BACKSTAGE_TOKEN']}"
    return h


def gh_headers() -> dict:
    cfg = get_config()
    return {
        "Authorization": f"token {cfg['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }


def github_owner_repo() -> tuple[str, str]:
    cfg = get_config()
    parts = cfg["GITHUB_REPO"].split("/", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else ("", "")
