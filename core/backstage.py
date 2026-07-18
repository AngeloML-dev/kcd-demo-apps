"""Interaccion con Backstage Scaffolder."""
import time
import requests
from .config import get_config
from .helpers import bs_headers, gh_headers, github_owner_repo


def step_backstage(intent: dict) -> tuple[bool, str]:
    """Llama al Scaffolder de Backstage. Retorna (exito, task_id)."""
    cfg = get_config()
    gh_owner, gh_repo = github_owner_repo()

    template_ref = ("template:default/api-with-database"
                    if intent.get("has_database")
                    else "template:default/microservice-template")

    values = {
        "service_name": intent["service_name"],
        "owner": intent.get("owner", "backend-team"),
        "environment": intent["environment"],
        "replicas": intent["replicas"],
        "github_repo_owner": gh_owner,
        "github_repo_name": gh_repo,
    }
    values["port"] = intent.get("port", 8080)
    if intent.get("has_database"):
        values["db_storage"] = "1Gi"
    else:
        values["description"] = intent.get("description", "Microservicio")
        values["has_health_check"] = True

    try:
        body = {"templateRef": template_ref, "values": values}
        if cfg["GITHUB_TOKEN"]:
            body["secrets"] = {"githubToken": cfg["GITHUB_TOKEN"]}

        resp = requests.post(
            f"{cfg['BACKSTAGE_URL']}/api/scaffolder/v2/tasks",
            headers=bs_headers(),
            json=body,
            timeout=30
        )
        if resp.status_code in (200, 201):
            task_id = resp.json().get("id", "")
            return True, task_id
        return False, ""
    except Exception:
        return False, ""


def wait_backstage_task(task_id: str, timeout: int = 90) -> str:
    """Espera task y retorna PR URL o ''."""
    cfg = get_config()
    url = f"{cfg['BACKSTAGE_URL']}/api/scaffolder/v2/tasks/{task_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        pr_url = _poll_task(task_id, url)
        if pr_url is not None:
            return pr_url
        time.sleep(2)
    return ""


def _poll_task(task_id: str, url: str):
    """Retorna PR URL si completo, '' si fallo, None si aun corriendo."""
    try:
        r = requests.get(url, headers=bs_headers(), timeout=10)
        if r.ok:
            data = r.json()
            st = data.get("status", "")
            if st == "completed":
                events = _get_task_events(task_id)
                pr_url = _extract_pr_url_from_events(events)
                if pr_url:
                    return pr_url
                pr_url = _extract_pr_url_from_data(data)
                if pr_url:
                    return pr_url
                pr_url = _find_recent_pr()
                if pr_url:
                    return pr_url
                return ""
            if st in ("failed", "cancelled"):
                return ""
    except requests.exceptions.ConnectionError:
        pr_url = _find_recent_pr()
        if pr_url:
            return pr_url
        return ""
    except Exception:
        pass
    return None


def _get_task_events(task_id: str) -> list:
    cfg = get_config()
    try:
        r = requests.get(
            f"{cfg['BACKSTAGE_URL']}/api/scaffolder/v2/tasks/{task_id}/events",
            headers=bs_headers(), timeout=10
        )
        if r.ok:
            return r.json() if isinstance(r.json(), list) else []
    except Exception:
        pass
    return []


def _extract_pr_url_from_events(events: list) -> str:
    for event in events:
        body = event.get("body", {})
        if not isinstance(body, dict):
            continue
        output = body.get("output", {})
        if isinstance(output, dict):
            for link in output.get("links", []):
                url = link.get("url", "")
                if url and ("pull" in url or "github.com" in url):
                    return url
            if output.get("remoteUrl", ""):
                return output["remoteUrl"]
        for key in ("remoteUrl", "pullRequestUrl"):
            if body.get(key, ""):
                return body[key]
        for link in body.get("links", []):
            url = link.get("url", "")
            if url and ("pull" in url or "github.com" in url):
                return url
    return ""


def _extract_pr_url_from_data(data: dict) -> str:
    output = data.get("output", {})
    if isinstance(output, dict):
        for link in output.get("links", []):
            link_url = link.get("url", "")
            if link_url and ("pull" in link_url.lower() or "github.com" in link_url):
                return link_url
        if output.get("remoteUrl", ""):
            return output["remoteUrl"]
    state = data.get("state", {})
    if isinstance(state, dict):
        for key in ("output", "publish-to-github", "publish"):
            step_data = state.get(key, {})
            if isinstance(step_data, dict):
                for link in step_data.get("links", []):
                    link_url = link.get("url", "")
                    if link_url and ("pull" in link_url.lower() or "github.com" in link_url):
                        return link_url
                if step_data.get("remoteUrl", ""):
                    return step_data["remoteUrl"]
    for step in data.get("steps", []):
        step_output = step.get("output", {})
        if isinstance(step_output, dict):
            if step_output.get("remoteUrl", ""):
                return step_output["remoteUrl"]
            if step_output.get("pullRequestUrl", ""):
                return step_output["pullRequestUrl"]
    return ""


def _find_recent_pr() -> str:
    cfg = get_config()
    if not cfg["GITHUB_TOKEN"] or not cfg["GITHUB_REPO"]:
        return ""
    try:
        r = requests.get(
            f"https://api.github.com/repos/{cfg['GITHUB_REPO']}/pulls?state=open&sort=created&direction=desc&per_page=1",
            headers=gh_headers(), timeout=10
        )
        if r.ok and r.json():
            return r.json()[0].get("html_url", "")
    except Exception:
        pass
    return ""
