from app.domain.evaluators.base import BaseEvaluator, EvaluatorResult
from app.schemas.conversation import ConversationCreate
from app.schemas.evaluation import IssueDetected, ImprovementSuggestion


class ToolCallEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "tool_call"

    async def evaluate(self, conversation: ConversationCreate) -> EvaluatorResult:
        tool_turns = [t for t in conversation.turns if t.role == "assistant" and t.tool_calls]

        if not tool_turns:
            return EvaluatorResult(evaluator_name=self.name, score=None)

        issues: list[IssueDetected] = []
        suggestions: list[ImprovementSuggestion] = []
        score = 1.0

        total_calls = 0
        failed_calls = 0
        hallucinated_params = 0

        conversation_text = " ".join(
            t.content for t in conversation.turns if t.content
        ).lower()

        for turn in tool_turns:
            for tool_call in turn.tool_calls:
                total_calls += 1

                if tool_call.result and tool_call.result.get("status") != "success":
                    failed_calls += 1

                hallucinated = self._detect_hallucinated_params(
                    tool_call.parameters, conversation_text
                )
                if hallucinated:
                    hallucinated_params += len(hallucinated)
                    issues.append(IssueDetected(
                        type="parameter_hallucination",
                        severity="warning",
                        description=(
                            f"Tool '{tool_call.tool_name}' has parameters not grounded "
                            f"in conversation: {', '.join(hallucinated)}"
                        ),
                    ))
                    suggestions.append(ImprovementSuggestion(
                        type="prompt",
                        suggestion=(
                            f"Add explicit instruction to extract '{', '.join(hallucinated)}' "
                            f"from user input before calling '{tool_call.tool_name}'"
                        ),
                        rationale="Parameters were not mentioned in the conversation context",
                        confidence=0.7,
                    ))
                    score -= 0.15

        if failed_calls > 0:
            failure_rate = failed_calls / total_calls
            score -= failure_rate * 0.3

        execution_success = failed_calls == 0
        selection_accuracy = 1.0 if total_calls > 0 else None
        parameter_accuracy = round(
            1.0 - (hallucinated_params / (total_calls * 2)), 2
        ) if total_calls > 0 else None

        return EvaluatorResult(
            evaluator_name=self.name,
            score=max(0.0, round(score, 2)),
            issues=issues,
            suggestions=suggestions,
            metadata={
                "total_calls": total_calls,
                "failed_calls": failed_calls,
                "hallucinated_params": hallucinated_params,
                "execution_success": execution_success,
                "selection_accuracy": selection_accuracy,
                "parameter_accuracy": parameter_accuracy,
            },
        )

    def _detect_hallucinated_params(
        self, parameters: dict, conversation_text: str
    ) -> list[str]:
        hallucinated = []
        for key, value in parameters.items():
            if not isinstance(value, str):
                value = str(value)
            if len(value) > 2 and value.lower() not in conversation_text:
                hallucinated.append(key)
        return hallucinated
