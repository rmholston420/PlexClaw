from __future__ import annotations

DEFAULT_CLOUD_MODELS = [
    "claude-sonnet-4-5",
    "claude-opus-4-5",
    "claude-haiku-4-5",
]

# Canonical Anthropic API model IDs — use these when submitting to the real SDK.
# The short aliases above are accepted by the latest Anthropic SDK (>=0.30) which
# resolves them server-side, but if you need fully-qualified IDs for strict
# validation or older SDK versions, use these instead:


# Fallback to dated identifiers accepted by the Anthropic API for strict mode:
