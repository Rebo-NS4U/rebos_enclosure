#!/usr/bin/env python3
"""Launch Dweebo's Codex ACP agent through an OmniRoute gateway."""
import json
import os
from pathlib import Path
import shutil
import sys
from urllib.parse import urlsplit


def launch_environment(environment):
    env = dict(environment)
    directory = Path(env.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "dweebo"
    path = directory / "omniroute.json"
    settings = {}
    if path.is_file():
        if path.stat().st_mode & 0o077:
            raise ValueError("Set permissions to 600 on " + str(path))
        settings = json.loads(path.read_text())
        if not isinstance(settings, dict):
            raise ValueError("omniroute.json must contain a JSON object.")

    def setting(name, default=""):
        value = env.get("OMNIROUTE_" + name.upper(), settings.get(name, default))
        if not isinstance(value, str):
            raise ValueError(f"OmniRoute {name} must be a string.")
        return value.strip()

    model = setting("model")
    if not model:
        raise ValueError("Set a model or combo in ~/.config/dweebo/omniroute.json or OMNIROUTE_MODEL.")
    key = setting("api_key")
    base_url = setting("base_url", "http://127.0.0.1:20128/v1").rstrip("/")
    endpoint = urlsplit(base_url)
    has_query_or_fragment = bool(endpoint.query or endpoint.fragment)
    if (endpoint.scheme not in ("http", "https") or not endpoint.hostname
            or endpoint.username is not None or has_query_or_fragment
            or not endpoint.path.endswith("/v1")):
        raise ValueError("Set OmniRoute base_url to an HTTP(S) API root ending in /v1.")

    config = json.loads(env.get("CODEX_CONFIG", "{}"))
    if not isinstance(config, dict):
        raise ValueError("CODEX_CONFIG must be a JSON object.")
    provider_id = "dweebo_omniroute"
    provider = dict(name="OmniRoute", base_url=base_url, wire_api="responses", requires_openai_auth=False)
    if key:
        env["OMNIROUTE_API_KEY"] = key
        provider["env_key"] = "OMNIROUTE_API_KEY"

    config.setdefault("sandbox_workspace_write", {}).setdefault("network_access", True)
    config.setdefault("features", {})["memories"] = False
    config.setdefault("memories", {}).update(generate_memories=False, use_memories=False)
    config.setdefault("model_providers", {})[provider_id] = provider
    config.update(model=model, model_provider=provider_id)
    env.update(
        CODEX_CONFIG=json.dumps(config),
        MODEL_PROVIDER=provider_id,
        INITIAL_AGENT_MODE="workspace-write",
        REBOS_CODEX_BINARY=shutil.which("codex", path=env.get("PATH")) or "codex",
        CODEX_PATH=str(Path(__file__).with_name("codex_workspace.py")),
    )
    return env


def main():
    try:
        env = launch_environment(os.environ)
    except (ValueError, OSError) as error:
        print("Dweebo OmniRoute: " + str(error), file=sys.stderr)
        return 1
    os.execvpe("npx", ["npx", "-y", "@agentclientprotocol/codex-acp"], env)


if __name__ == "__main__":
    raise SystemExit(main())
