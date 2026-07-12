from __future__ import annotations

# Canonical Anthropic API model IDs accepted as of July 2026.
# These are the short alias IDs that the Anthropic API resolves to
# the latest stable point release of each family tier.
DEFAULT_CLOUD_MODELS = [
    "claude-sonnet-4-5",
    "claude-opus-4-5",
    "claude-haiku-4-5",
]

# claude-sonnet-4-5 is the recommended default: strong coding performance,
# fastest time-to-first-token in the Sonnet tier, accepted by all
# Agent SDK ClaudeAgentOptions model= fields.
DEFAULT_CLOUD_MODEL = "claude-sonnet-4-5"
