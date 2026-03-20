import json
import logging

import httpx

from app.core.config import Settings
from app.domain.self_updater.pattern_detector import FailurePattern

logger = logging.getLogger(__name__)

_FALLBACK_RULES: dict[str, tuple[str, str, str, float]] = {
    "hallucinated_parameter": ("tool", "Tighten parameter schemas; reject calls with undeclared keys.", "Hallucinated parameters introduce incorrect data into tool calls, causing downstream failures.", 0.85),
    "tool_not_called": ("prompt", "Add explicit tool-use examples to the system prompt.", "Agents skip tool calls when the prompt lacks clear triggering examples.", 0.80),
    "parameter_error": ("tool", "Add stricter JSON schema validation for tool inputs.", "Malformed parameters fail silently without schema enforcement.", 0.82),
    "empty_response": ("prompt", "Add a fallback instruction: never return an empty reply.", "Empty responses break user experience and indicate missing fallback handling.", 0.90),
    "mission_incomplete": ("training", "Flag for RLHF: reward completion of stated user goal.", "Agent consistently abandons goals mid-conversation, indicating reward misalignment.", 0.75),
    "context_lost": ("prompt", "Inject a context-summary block at the start of each system prompt.", "Long conversations cause context window truncation, losing early user preferences.", 0.78),
    "contradicts_previous": ("training", "Flag contradictory turns for fine-tuning on consistency.", "Self-contradictions erode user trust and indicate poor context retention.", 0.72),
    "format": ("prompt", "Add output format examples to the system prompt covering edge cases.", "Format failures indicate the agent lacks clear formatting constraints.", 0.70),
    "latency": ("tool", "Add timeout constraints and caching for slow tool calls.", "High latency degrades user experience and may indicate missing optimisations.", 0.75),
    "parameter_hallucination": ("tool", "Tighten tool parameter schemas; add grounding validation to reject parameters not found in context.", "Parameters are being inferred without grounding in user utterances, causing incorrect tool calls.", 0.88),
}

_PROMPT = """You are a senior AI systems engineer reviewing failure patterns in an AI agent.

Detected recurring failure patterns:
{patterns}

For each pattern, generate one actionable improvement suggestion. Respond with ONLY a JSON array:
[
  {{
    "pattern_type": "<pattern_type>",
    "category": "prompt|tool|training",
    "suggestion": "<one concrete, actionable recommendation>",
    "rationale": "<why this fix addresses the root cause>",
    "confidence": <float between 0.0 and 1.0 indicating how confident you are this fix will help>
  }}
]

Rules:
- category "prompt" = fix the system prompt or few-shot examples
- category "tool" = fix tool definitions, parameter schemas, or selection logic
- category "training" = flag for fine-tuning or RLHF
- Be specific. No vague advice.
- confidence should reflect how directly the fix addresses the observed pattern."""


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
        rule = _FALLBACK_RULES.get(p.pattern_type)
        if rule:
            category, suggestion, rationale, confidence = rule
        else:
            category, suggestion, rationale, confidence = (
                "training", "Review failures manually.",
                "Pattern not recognised; manual review needed to determine root cause.", 0.50,
            )
        result.append({
            "pattern_type": p.pattern_type,
            "category": category,
            "suggestion": suggestion,
            "rationale": rationale,
            "confidence": confidence,
        })
    return result
