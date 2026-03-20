import json
import logging

import httpx

from app.core.config import Settings
from app.domain.self_updater.pattern_detector import FailurePattern

logger = logging.getLogger(__name__)

_FALLBACK_RULES: dict[str, tuple[str, str]] = {
    "hallucinated_parameter": ("tool", "Tighten parameter schemas; reject calls with undeclared keys."),
    "tool_not_called": ("prompt", "Add explicit tool-use examples to the system prompt."),
    "parameter_error": ("tool", "Add stricter JSON schema validation for tool inputs."),
    "empty_response": ("prompt", "Add a fallback instruction: never return an empty reply."),
    "mission_incomplete": ("training", "Flag for RLHF: reward completion of stated user goal."),
    "context_lost": ("prompt", "Inject a context-summary block at the start of each system prompt."),
    "contradicts_previous": ("training", "Flag contradictory turns for fine-tuning on consistency."),
}

_PROMPT = """You are a senior AI systems engineer reviewing failure patterns in an AI agent.

Detected recurring failure patterns:
{patterns}

For each pattern, generate one actionable improvement suggestion. Respond with ONLY a JSON array:
[
  {{
    "pattern_type": "<pattern_type>",
    "category": "prompt|tool|training",
    "suggestion": "<one concrete, actionable recommendation>"
  }}
]

Rules:
- category "prompt" = fix the system prompt or few-shot examples
- category "tool" = fix tool definitions, parameter schemas, or selection logic
- category "training" = flag for fine-tuning or RLHF
- Be specific. No vague advice."""


async def generate_suggestions(
    patterns: list[FailurePattern],
    settings: Settings,
) -> list[dict]:
    if not patterns:
        return []

    pattern_lines = "\n".join(
        f"- {p.pattern_type} (occurred {p.occurrences}x): "
        + ("; ".join(p.example_issues) if p.example_issues else "no examples")
        for p in patterns
    )
    prompt = _PROMPT.format(patterns=pattern_lines)

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            res = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
            )
            res.raise_for_status()
            text = res.json().get("response", "").strip()
            start, end = text.find("["), text.rfind("]") + 1
            if start == -1 or end == 0:
                return _fallback_suggestions(patterns)
            return json.loads(text[start:end])
    except Exception as exc:
        logger.warning("Suggestion generation failed: %s", exc)
        return _fallback_suggestions(patterns)


def _fallback_suggestions(patterns: list[FailurePattern]) -> list[dict]:
    result = []
    for p in patterns:
        category, suggestion = _FALLBACK_RULES.get(p.pattern_type, ("training", "Review failures manually."))
        result.append({
            "pattern_type": p.pattern_type,
            "category": category,
            "suggestion": suggestion,
        })
    return result
