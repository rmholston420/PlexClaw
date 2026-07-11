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
CANONICAL_CLOUD_MODELS = [
    "claude-sonnet-4-5",          # claude-sonnet-4-5 (2025 release, latest sonnet)
    "claude-opus-4-5",            # claude-opus-4-5   (2025 release, latest opus)
    "claude-haiku-4-5",           # claude-haiku-4-5  (2025 release, latest haiku)
]

# Fallback to dated identifiers accepted by the Anthropic API for strict mode:
STABLE_CLOUD_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307",
]
