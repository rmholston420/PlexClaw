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
    print("claude_agent_sdk_version=", version)
    print("ANTHROPIC_API_KEY_present=", bool(os.getenv("ANTHROPIC_API_KEY")))
    print("ANTHROPIC_BASE_URL=", os.getenv("ANTHROPIC_BASE_URL", ""))
    print("OLLAMA_BASE_URL=", os.getenv("OLLAMA_BASE_URL", ""))
    print("cwd=", os.getcwd())

    required = ["ANTHROPIC_API_KEY"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(
            f"FAIL: missing required environment variables: {joined}"
        )

    opts = ClaudeAgentOptions(
        permission_mode="plan",
        allowed_tools=["Read", "Glob", "Grep"],
        max_turns=1,
    )
    print("options_ok=", isinstance(opts, ClaudeAgentOptions))
    print("client_class=", ClaudeSDKClient)


if __name__ == "__main__":
    main()
