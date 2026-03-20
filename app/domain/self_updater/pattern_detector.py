from collections import Counter
from dataclasses import dataclass

from app.db.models.evaluation import Evaluation


@dataclass
class FailurePattern:
    pattern_type: str
    occurrences: int
    example_issues: list[str]
    affected_versions: list[str]


def detect_patterns(
    evaluations: list[Evaluation],
    min_occurrences: int,
) -> list[FailurePattern]:
    issue_counter: Counter[str] = Counter()
    issue_examples: dict[str, list[str]] = {}
    issue_versions: dict[str, set[str]] = {}

    for ev in evaluations:
        for issue in (ev.issues_detected or []):
            itype = issue.get("type", "unknown")
            issue_counter[itype] += 1
            issue_examples.setdefault(itype, [])
            if len(issue_examples[itype]) < 3:
                desc = issue.get("description", "")
                if desc:
                    issue_examples[itype].append(desc)
            issue_versions.setdefault(itype, set()).add(ev.conversation_id)

    patterns = []
    for itype, count in issue_counter.items():
        if count >= min_occurrences:
            patterns.append(FailurePattern(
                pattern_type=itype,
                occurrences=count,
                example_issues=issue_examples.get(itype, []),
                affected_versions=list(issue_versions.get(itype, set())),
            ))

    patterns.sort(key=lambda p: p.occurrences, reverse=True)
    return patterns
