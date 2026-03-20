import json
import logging

import httpx
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.domain.evaluators.base import BaseEvaluator, EvaluatorResult
from app.schemas.conversation import ConversationCreate

logger = logging.getLogger(__name__)

_PROMPT = """You are evaluating an AI assistant's response quality.

Conversation so far:
{context}

Assistant response:
{response}

Rate this response strictly on a 0.0 to 1.0 scale for:
- quality: clarity, coherence, and correctness
- helpfulness: how well it addresses the user's actual need
- factuality: accuracy, no hallucinations or made-up information

Reply with ONLY a JSON object, no explanation outside it:
{{"quality": 0.0, "helpfulness": 0.0, "factuality": 0.0, "reasoning": "one line"}}"""


class LLMJudgeEvaluator(BaseEvaluator):
    def __init__(self) -> None:
        self._settings: Settings = get_settings()

    @property
    def name(self) -> str:
        return "llm_judge"

    async def evaluate(self, conversation: ConversationCreate) -> EvaluatorResult:
        if not self._settings.llm_enabled:
            return EvaluatorResult(evaluator_name=self.name, score=None)

        cache = Redis.from_url(self._settings.redis_url, decode_responses=True)

        try:
            cache_key = f"llm_judge:{conversation.conversation_id}:{self._settings.ollama_model}"
            try:
                cached = await cache.get(cache_key)
            except Exception:
                cached = None
            if cached:
                data = json.loads(cached)
                return EvaluatorResult(
                    evaluator_name=self.name,
                    score=data["score"],
                    metadata=data.get("metadata", {}),
                )

            assistant_turns = [t for t in conversation.turns if t.role == "assistant"]
            if not assistant_turns:
                return EvaluatorResult(evaluator_name=self.name, score=None)

            turn_scores = []
            for turn in assistant_turns:
                idx = next(i for i, t in enumerate(conversation.turns) if t.turn_id == turn.turn_id)
                context = "\n".join(
                    f"{t.role}: {t.content}" for t in conversation.turns[:idx]
                )
                scores = await self._score(context, turn.content)
                if scores:
                    turn_scores.append(scores)

            if not turn_scores:
                return EvaluatorResult(evaluator_name=self.name, score=None)

            quality = round(sum(s["quality"] for s in turn_scores) / len(turn_scores), 2)
            helpfulness = round(sum(s["helpfulness"] for s in turn_scores) / len(turn_scores), 2)
            factuality = round(sum(s["factuality"] for s in turn_scores) / len(turn_scores), 2)
            overall = round((quality + helpfulness + factuality) / 3, 2)

            meta = {"quality": quality, "helpfulness": helpfulness, "factuality": factuality}

            try:
                await cache.setex(
                    cache_key,
                    self._settings.llm_cache_ttl_seconds,
                    json.dumps({"score": overall, "metadata": meta}),
                )
            except Exception:
                pass

            return EvaluatorResult(evaluator_name=self.name, score=overall, metadata=meta)
        finally:
            await cache.aclose()

    async def _score(self, context: str, response: str) -> dict | None:
        prompt = _PROMPT.format(context=context or "(start of conversation)", response=response)
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
            logger.warning("LLM judge scoring failed: %s", exc)
            return None
