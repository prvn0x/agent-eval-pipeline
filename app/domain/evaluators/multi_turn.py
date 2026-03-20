import json
import logging

import httpx

from app.core.config import Settings, get_settings
from app.domain.evaluators.base import BaseEvaluator, EvaluatorResult
from app.schemas.conversation import ConversationCreate
from app.schemas.evaluation import IssueDetected

logger = logging.getLogger(__name__)

_PROMPT = """You are evaluating a multi-turn conversation between a user and an AI assistant.

Conversation:
{conversation}

Evaluate the assistant's performance across all turns on:
- coherence: does each response logically follow the conversation flow?
- consistency: does the assistant contradict itself or forget prior context?
- context_handling: does the assistant correctly reference and use earlier information?

Reply with ONLY a JSON object:
{{"coherence": 0.0, "consistency": 0.0, "context_handling": 0.0, "issues": []}}

For issues, use format: ["brief description of any problem found"]"""


class MultiTurnEvaluator(BaseEvaluator):
    def __init__(self) -> None:
        self._settings: Settings = get_settings()

    @property
    def name(self) -> str:
        return "multi_turn"

    async def evaluate(self, conversation: ConversationCreate) -> EvaluatorResult:
        if len(conversation.turns) < 3:
            return EvaluatorResult(evaluator_name=self.name, score=None)

        conv_text = "\n".join(
            f"{t.role.upper()}: {t.content}" for t in conversation.turns
        )

        result = await self._evaluate(conv_text)
        if not result:
            return EvaluatorResult(evaluator_name=self.name, score=None)

        coherence = result.get("coherence", 1.0)
        consistency = result.get("consistency", 1.0)
        context_handling = result.get("context_handling", 1.0)
        overall = round((coherence + consistency + context_handling) / 3, 2)

        issues = []
        for issue_text in result.get("issues", []):
            if issue_text:
                issues.append(IssueDetected(
                    type="coherence",
                    severity="warning",
                    description=issue_text,
                ))

        return EvaluatorResult(
            evaluator_name=self.name,
            score=overall,
            issues=issues,
            metadata={
                "coherence": round(coherence, 2),
                "consistency": round(consistency, 2),
                "context_handling": round(context_handling, 2),
            },
        )

    async def _evaluate(self, conversation_text: str) -> dict | None:
        prompt = _PROMPT.format(conversation=conversation_text)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    f"{self._settings.ollama_base_url}/api/generate",
                    json={"model": self._settings.ollama_model, "prompt": prompt, "stream": False},
                )
                res.raise_for_status()
                text = res.json().get("response", "").strip()
                start, end = text.find("{"), text.rfind("}") + 1
                if start == -1 or end == 0:
                    return None
                return json.loads(text[start:end])
        except Exception as exc:
            logger.warning("Multi-turn evaluation failed: %s", exc)
            return None
