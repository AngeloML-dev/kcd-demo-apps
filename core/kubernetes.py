"""Operaciones con kubectl."""
import subprocess
import time


def wait_for_pods(intent: dict, timeout: int = 90) -> bool:
    """Espera a que el deployment tenga todas las replicas ready."""
    name, ns = intent["service_name"], intent["environment"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run(
            ["kubectl", "get", "deployment", name, "-n", ns,
             "--no-headers", "-o",
             "jsonpath={.status.readyReplicas}/{.spec.replicas}"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and "/" in r.stdout:
            ready, total = r.stdout.strip().split("/")
            if ready and ready == total and int(ready) > 0:
                return True
        time.sleep(3)
    return False


def get_pods(namespace: str) -> list[dict]:
    """Retorna lista de pods en un namespace."""
    r = subprocess.run(
        ["kubectl", "get", "pods", "-n", namespace, "--no-headers"],
        capture_output=True, text=True, timeout=10
    )
    pods = []
    if r.returncode == 0:
        for line in r.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 5:
                pods.append({
                    "name": parts[0], "ready": parts[1],
                    "status": parts[2], "age": parts[4]
                })
    return pods
