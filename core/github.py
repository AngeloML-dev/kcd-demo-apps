"""Operaciones directas con GitHub API (fallback y merge)."""
import base64
import requests
from .config import get_config
from .helpers import gh_headers


def generate_manifest(intent: dict) -> str:
    """Genera el manifest YAML a partir del intent."""
    name = intent["service_name"]
    env = intent["environment"]
    owner = intent.get("owner", "backend-team")
    replicas = intent["replicas"]
    port = intent.get("port", 8080)

    manifest = f"""# Generado por KCD Demo Agent
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {env}
  labels:
    app: {name}
    managed-by: kcd-demo-agent
    environment: {env}
    owner: {owner}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
        environment: {env}
    spec:
      containers:
        - name: {name}
          image: nginx:alpine
          ports:
            - containerPort: {port}
              name: http
          resources:
            requests:
              memory: "64Mi"
              cpu: "50m"
            limits:
              memory: "128Mi"
              cpu: "100m"
---
apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {env}
  labels:
    app: {name}
    managed-by: kcd-demo-agent
spec:
  selector:
    app: {name}
  ports:
    - name: http
      port: 80
      targetPort: {port}
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {name}
  namespace: {env}
  labels:
    app: {name}
    managed-by: kcd-demo-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {name}
  minReplicas: {replicas}
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 80
"""

    if intent.get("has_database"):
        manifest += f"""---
# PostgreSQL
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}-db
  namespace: {env}
  labels:
    app: {name}-db
    managed-by: kcd-demo-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {name}-db
  template:
    metadata:
      labels:
        app: {name}-db
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          env:
            - name: POSTGRES_DB
              value: {name}
            - name: POSTGRES_USER
              value: appuser
            - name: POSTGRES_PASSWORD
              value: kcd-demo-pass
          ports:
            - containerPort: 5432
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: {name}-db
  namespace: {env}
spec:
  selector:
    app: {name}-db
  ports:
    - port: 5432
      targetPort: 5432
"""
    return manifest


def create_pr_via_github(intent: dict) -> str:
    """Crea manifest y PR directamente via GitHub API (fallback)."""
    cfg = get_config()
    if not cfg["GITHUB_TOKEN"] or not cfg["GITHUB_REPO"]:
        return ""

    name = intent["service_name"]
    env = intent["environment"]
    branch = f"deploy/{name}-{env}"
    file_path = f"apps/{env}/{name}.yaml"
    manifest = generate_manifest(intent)

    api = f"https://api.github.com/repos/{cfg['GITHUB_REPO']}"
    headers = gh_headers()

    try:
        r = requests.get(f"{api}/git/ref/heads/main", headers=headers, timeout=10)
        if not r.ok:
            return ""
        main_sha = r.json()["object"]["sha"]

        r = requests.post(f"{api}/git/refs", headers=headers, timeout=10,
                          json={"ref": f"refs/heads/{branch}", "sha": main_sha})
        if r.status_code not in (200, 201, 422):
            return ""

        if r.status_code == 422:
            r = requests.get(f"{api}/git/ref/heads/{branch}", headers=headers, timeout=10)
            if not r.ok:
                return ""

        content_b64 = base64.b64encode(manifest.encode()).decode()
        r_existing = requests.get(f"{api}/contents/{file_path}?ref={branch}",
                                  headers=headers, timeout=10)
        put_data = {
            "message": f"feat: deploy {name} to {env} [{intent['replicas']} replicas]",
            "content": content_b64,
            "branch": branch,
        }
        if r_existing.ok:
            put_data["sha"] = r_existing.json()["sha"]

        r = requests.put(f"{api}/contents/{file_path}", headers=headers,
                         json=put_data, timeout=15)
        if r.status_code not in (200, 201):
            return ""

        db_text = " con PostgreSQL" if intent.get("has_database") else ""
        r = requests.post(f"{api}/pulls", headers=headers, timeout=15,
                          json={
                              "title": f"feat: deploy {name}{db_text} to {env}",
                              "body": f"Deployment generado por KCD Demo Agent\n\n"
                                      f"- **Servicio:** {name}\n"
                                      f"- **Ambiente:** {env}\n"
                                      f"- **Replicas:** {intent['replicas']}\n"
                                      f"- **Owner:** {intent.get('owner', 'backend-team')}\n",
                              "head": branch,
                              "base": "main",
                          })
        if r.status_code in (200, 201):
            return r.json().get("html_url", "")
        return ""
    except Exception:
        return ""


def merge_pull_request(pr_url: str) -> bool:
    """Auto-merge del PR."""
    cfg = get_config()
    try:
        pr_number = pr_url.rstrip("/").split("/")[-1]
        api_url = f"https://api.github.com/repos/{cfg['GITHUB_REPO']}/pulls/{pr_number}/merge"
        r = requests.put(
            api_url, headers=gh_headers(),
            json={"commit_title": "merge: deploy via Backstage [KCD Demo]",
                  "merge_method": "squash"},
            timeout=30
        )
        return r.status_code in (200, 201)
    except Exception:
        return False
