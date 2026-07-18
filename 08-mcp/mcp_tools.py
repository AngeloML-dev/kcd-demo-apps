"""
MCP Tool Manager — conecta a Kubernetes y GitHub MCP servers.
Expone tools como funciones simples para el agente.
"""
import json
import os
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ── MCP Server configs ──────────────────────────────────────
def _k8s_server_params() -> StdioServerParameters:
    """Kubernetes MCP server via npx."""
    return StdioServerParameters(
        command="npx",
        args=["-y", "mcp-server-kubernetes"],
    )


def _github_server_params() -> StdioServerParameters:
    """GitHub MCP server via Docker."""
    token = os.getenv("GITHUB_TOKEN", "")
    return StdioServerParameters(
        command="docker",
        args=[
            "run", "-i", "--rm",
            "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server",
        ],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": token},
    )


# ── Tools que nos interesan para la demo ────────────────────
# Filtramos para no mandar 30+ tools al LLM (mas rapido y preciso)
K8S_TOOLS_FILTER = {
    "get_pod_logs", "list_pods", "get_pods", "get_pod",
    "list_deployments", "get_deployments", "get_deployment",
    "describe_pod", "describe_deployment",
    "list_services", "get_services",
    "list_namespaces", "get_namespaces",
    "get_events", "list_events",
    "kubectl_get", "kubectl_describe",
    # Nombres genericos que usan algunos MCP servers
    "get_resources", "list_resources",
}

GH_TOOLS_FILTER = {
    "create_pull_request", "merge_pull_request",
    "get_pull_request", "list_pull_requests",
    "get_file_contents", "create_or_update_file",
    "create_branch", "list_branches",
    "create_ref", "get_ref",
    "push_files",
}


# ── MCP Client wrapper ─────────────────────────────────────
class MCPToolManager:
    """Manages connections to MCP servers and exposes tool calling."""

    def __init__(self):
        self._k8s_session: ClientSession | None = None
        self._gh_session: ClientSession | None = None
        self._k8s_tools: list[dict] = []
        self._gh_tools: list[dict] = []
        self._exit_stack = AsyncExitStack()

    async def connect_kubernetes(self) -> bool:
        """Connect to Kubernetes MCP server."""
        try:
            params = _k8s_server_params()
            read, write = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
            session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()

            tools_result = await session.list_tools()
            self._k8s_tools = [
                {"name": t.name, "description": t.description or "",
                 "schema": t.inputSchema if hasattr(t, 'inputSchema') else {}}
                for t in tools_result.tools
            ]
            self._k8s_session = session
            return True
        except Exception as e:
            print(f"  [!] Kubernetes MCP: {e}")
            return False

    async def connect_github(self) -> bool:
        """Connect to GitHub MCP server."""
        token = os.getenv("GITHUB_TOKEN", "")
        if not token or token.startswith("ghp_xxx"):
            return False
        try:
            params = _github_server_params()
            read, write = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
            session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()

            tools_result = await session.list_tools()
            self._gh_tools = [
                {"name": t.name, "description": t.description or "",
                 "schema": t.inputSchema if hasattr(t, 'inputSchema') else {}}
                for t in tools_result.tools
            ]
            self._gh_session = session
            return True
        except Exception as e:
            print(f"  [!] GitHub MCP: {e}")
            return False

    def get_all_tools(self) -> list[dict]:
        """Return all available tools as dicts for the LLM."""
        tools = []
        for t in self._k8s_tools:
            tools.append({**t, "source": "kubernetes"})
        for t in self._gh_tools:
            tools.append({**t, "source": "github"})
        return tools

    def get_tools_for_ollama(self, filter_names: set | None = None) -> list[dict]:
        """Format tools as Ollama-compatible function definitions.
        Si filter_names se pasa, solo incluye esos tools.
        Si no, aplica el filtro por defecto para mantenerlo ligero."""
        all_tools = self.get_all_tools()

        # Aplicar filtro: solo tools relevantes para la demo
        if filter_names is None:
            allowed = K8S_TOOLS_FILTER | GH_TOOLS_FILTER
        else:
            allowed = filter_names

        ollama_tools = []
        for t in all_tools:
            # Si hay filtro, solo incluir los que matchean
            # Tambien incluir todos si el filtro esta vacio (sin restriccion)
            if allowed and t["name"] not in allowed:
                continue
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("schema", {}),
                }
            })

        # Si el filtro fue muy agresivo y no quedo nada, mandar todos
        if not ollama_tools:
            for t in all_tools:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t.get("schema", {}),
                    }
                })

        return ollama_tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Call a tool by name, routing to the correct MCP server."""
        k8s_names = {t["name"] for t in self._k8s_tools}
        gh_names = {t["name"] for t in self._gh_tools}

        session = None
        if name in k8s_names and self._k8s_session:
            session = self._k8s_session
        elif name in gh_names and self._gh_session:
            session = self._gh_session
        else:
            return json.dumps({"error": f"Tool '{name}' not found in any MCP server"})

        try:
            result = await session.call_tool(name, arguments=arguments)
            texts = []
            for content in result.content:
                if hasattr(content, 'text'):
                    texts.append(content.text)
                else:
                    texts.append(str(content))
            return "\n".join(texts) if texts else "OK"
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def close(self):
        """Close all MCP connections cleanly."""
        await self._exit_stack.aclose()
