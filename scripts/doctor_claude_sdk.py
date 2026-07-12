from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def main() -> None:
    try:
        import claude_agent_sdk
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
    except Exception as exc:
        raise SystemExit(
            f"FAIL: claude_agent_sdk import failed: {exc}"
        ) from exc

    version = getattr(claude_agent_sdk, "__version__", "unknown")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "")

    print("claude_agent_sdk_version=", version)
    print("ANTHROPIC_API_KEY_present=", bool(api_key))
    print("ANTHROPIC_BASE_URL=", base_url)
    print("OLLAMA_BASE_URL=", ollama_url)
    print("cwd=", os.getcwd())

    local_mode = bool(base_url)
    print("local_mode=", local_mode)

    if not api_key:
        raise SystemExit(
            "FAIL: ANTHROPIC_API_KEY must be non-empty. "
            "For local mode, use a placeholder like local-dev-token."
        )

    opts = ClaudeAgentOptions(
        permission_mode="plan",
        allowed_tools=["Read", "Glob", "Grep"],
        max_turns=1,
    )
    print("options_ok=", isinstance(opts, ClaudeAgentOptions))
    print("client_class=", ClaudeSDKClient)

    if local_mode:
        print("mode_ok= local-compatible-endpoint")
    else:
        print("mode_ok= cloud-default")


if __name__ == "__main__":
    main()
