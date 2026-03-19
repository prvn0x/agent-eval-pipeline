from app.domain.evaluators.base import BaseEvaluator, EvaluatorResult
from app.schemas.conversation import ConversationCreate
from app.schemas.evaluation import IssueDetected

_LATENCY_WARNING_MS = 1000
_LATENCY_CRITICAL_MS = 3000


class HeuristicEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "heuristic"

    async def evaluate(self, conversation: ConversationCreate) -> EvaluatorResult:
        issues: list[IssueDetected] = []
        score = 1.0
        total_tools = 0
        tool_failures = 0

        if conversation.metadata and conversation.metadata.total_latency_ms:
            latency = conversation.metadata.total_latency_ms
            if latency > _LATENCY_CRITICAL_MS:
                issues.append(IssueDetected(
                    type="latency",
                    severity="critical",
                    description=f"Latency {latency}ms exceeds {_LATENCY_CRITICAL_MS}ms threshold",
                ))
                score -= 0.3
            elif latency > _LATENCY_WARNING_MS:
                issues.append(IssueDetected(
                    type="latency",
                    severity="warning",
                    description=f"Latency {latency}ms exceeds {_LATENCY_WARNING_MS}ms target",
                ))
                score -= 0.1

        for turn in conversation.turns:
            if not turn.content or not turn.content.strip():
                issues.append(IssueDetected(
                    type="format",
                    severity="warning",
                    description=f"Turn {turn.turn_id} has empty content",
                ))
                score -= 0.05

        for turn in conversation.turns:
            for tool_call in turn.tool_calls:
                total_tools += 1
                if tool_call.result and tool_call.result.get("status") != "success":
                    tool_failures += 1
                    issues.append(IssueDetected(
                        type="tool_failure",
                        severity="warning",
                        description=f"Tool '{tool_call.tool_name}' failed in turn {turn.turn_id}",
                    ))
                    score -= 0.15

        if conversation.metadata and conversation.metadata.mission_completed is False:
            issues.append(IssueDetected(
                type="mission_incomplete",
                severity="warning",
                description="Conversation ended without completing the mission",
            ))
            score -= 0.2

        return EvaluatorResult(
            evaluator_name=self.name,
            score=max(0.0, round(score, 2)),
            issues=issues,
            metadata={"total_tools": total_tools, "tool_failures": tool_failures},
        )
