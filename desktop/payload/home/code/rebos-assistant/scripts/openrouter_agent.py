#!/usr/bin/env python3
"""Launch a free OpenRouter model inside Dweebo's Codex ACP backend."""
import json
import os
from pathlib import Path
import shutil
import sys

MODELS = {
    "free-code": "cohere/north-mini-code:free",
    "free-nemotron": "nvidia/nemotron-3-ultra-550b-a55b:free",
}


def launch_environment(selection, environment=None):
    env = dict(os.environ if environment is None else environment)
    key = env.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        config = Path(env.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        path = config / "dweebo/openrouter-api-key"
        if path.is_file():
            if path.stat().st_mode & 0o077:
                raise ValueError("Set permissions to 600 on " + str(path))
            key = path.read_text().strip()
    if not key:
        raise ValueError("Create ~/.config/dweebo/openrouter-api-key with your OpenRouter key (permissions 600).")
    env["OPENROUTER_API_KEY"] = key
    config = json.loads(env.get("CODEX_CONFIG", "{}"))
    if not isinstance(config, dict):
        raise ValueError("CODEX_CONFIG must be a JSON object")
    config.setdefault("sandbox_workspace_write", {}).setdefault("network_access", True)
    config.update({
        "model": MODELS[selection],
        "model_provider": "dweebo_openrouter",
        "features": {**config.get("features", {}), "memories": False},
        "memories": {**config.get("memories", {}), "generate_memories": False, "use_memories": False},
    })
    providers = config.setdefault("model_providers", {})
    providers["dweebo_openrouter"] = {
        "name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY", "wire_api": "responses",
        "requires_openai_auth": False,
    }
    env["CODEX_CONFIG"] = json.dumps(config)
    env["MODEL_PROVIDER"] = "dweebo_openrouter"
    env["INITIAL_AGENT_MODE"] = "workspace-write"
    env["REBOS_CODEX_BINARY"] = shutil.which("codex", path=env.get("PATH")) or "codex"
    env["CODEX_PATH"] = str(Path(__file__).with_name("codex_workspace.py"))
    return env


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MODELS:
        print("Choose free-code or free-nemotron", file=sys.stderr)
        return 2
    try:
        env = launch_environment(sys.argv[1])
    except (ValueError, OSError) as error:
        print("Dweebo OpenRouter: " + str(error), file=sys.stderr)
        return 1
    os.execvpe("npx", ["npx", "-y", "@agentclientprotocol/codex-acp"], env)


if __name__ == "__main__":
    raise SystemExit(main())
