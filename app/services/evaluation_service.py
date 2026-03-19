import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import ConversationStatus
from app.db.models.evaluation import Evaluation
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.evaluation_repository import EvaluationRepository
from app.domain.evaluators.base import BaseEvaluator, EvaluatorResult
from app.domain.evaluators.heuristic import HeuristicEvaluator
from app.schemas.conversation import ConversationCreate


class EvaluationService:
    def __init__(self, session: AsyncSession) -> None:
        self._conv_repo = ConversationRepository(session)
        self._eval_repo = EvaluationRepository(session)
        self._evaluators: list[BaseEvaluator] = [
            HeuristicEvaluator(),
        ]

    async def run(self, conversation_id: str) -> Evaluation:
        conv = await self._conv_repo.get_by_id(conversation_id)
        if not conv:
            raise ValueError(f"Conversation '{conversation_id}' not found")

        await self._conv_repo.update_status(conversation_id, ConversationStatus.PROCESSING)

        conversation = ConversationCreate(
            conversation_id=conv.id,
            agent_version=conv.agent_version,
            turns=conv.turns,
            feedback=conv.feedback,
            metadata=conv.conv_metadata,
        )

        results: list[EvaluatorResult] = []
        for evaluator in self._evaluators:
            result = await evaluator.evaluate(conversation)
            results.append(result)

        valid_scores = [r.score for r in results if r.score is not None]
        overall_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else 0.0

        all_issues = [issue for r in results for issue in r.issues]
        all_suggestions = [s for r in results for s in r.suggestions]

        heuristic = next((r for r in results if r.evaluator_name == "heuristic"), None)
        tool_meta = heuristic.metadata if heuristic else {}

        evaluation = Evaluation(
            id=f"eval_{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            overall_score=overall_score,
            issues_detected=[i.model_dump() for i in all_issues],
            improvement_suggestions=[s.model_dump() for s in all_suggestions],
            evaluator_scores={r.evaluator_name: r.score for r in results},
            tool_evaluation={
                "execution_success": tool_meta.get("tool_failures", 0) == 0,
                "total_tools": tool_meta.get("total_tools", 0),
                "tool_failures": tool_meta.get("tool_failures", 0),
            },
        )

        await self._eval_repo.create(evaluation)
        await self._conv_repo.update_status(conversation_id, ConversationStatus.COMPLETED)

        return evaluation
