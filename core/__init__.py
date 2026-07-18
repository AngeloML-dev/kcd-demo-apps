"""KCD Peru 2026 — Core compartido entre agent y web."""
from .config import load_env, get_config
from .checks import check_ollama, check_ollama_mlx, check_backstage, check_github, check_kubectl, check_argocd
from .intent import (
    classify_intent, chat_response, extract_intent, adjust_intent,
    get_missing_fields, apply_field,
    stream_chat_response, classify_and_route,
)
from .backstage import step_backstage, wait_backstage_task
from .github import generate_manifest, create_pr_via_github, merge_pull_request
from .argocd import argocd_sync
from .kubernetes import wait_for_pods, get_pods

__all__ = [
    "load_env", "get_config",
    "check_ollama", "check_ollama_mlx", "check_backstage", "check_github", "check_kubectl", "check_argocd",
    "classify_intent", "chat_response", "extract_intent", "adjust_intent",
    "get_missing_fields", "apply_field",
    "stream_chat_response", "classify_and_route",
    "step_backstage", "wait_backstage_task",
    "generate_manifest", "create_pr_via_github", "merge_pull_request",
    "argocd_sync",
    "wait_for_pods", "get_pods",
]
