from collections import Counter, defaultdict
from dataclasses import dataclass

_PASS_THRESHOLD = 0.7


@dataclass
class CalibrationResult:
    conversations_analyzed: int
    overall_agreement: float
    evaluator_calibration: list[dict]
    blind_spots: list[dict]


def calibrate(conversations: list[dict]) -> CalibrationResult:
    if not conversations:
        return CalibrationResult(0, 0.0, [], [])

    # {evaluator_name: {tp, tn, fp, fn}}
    ev_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "tn": 0, "fp": 0, "fn": 0})
    overall_matches = 0

    human_type_counts: Counter[str] = Counter()
    evaluator_caught: Counter[str] = Counter()

    for conv in conversations:
        evaluation = conv["evaluation"]
        agreement = conv["agreement"]
        annotation_types: list[str] = conv["annotation_types"]

        human_pass = agreement.routing_decision == "auto_label"
        evaluator_pass = (
            evaluation.overall_score is not None
            and evaluation.overall_score >= _PASS_THRESHOLD
        )
        if human_pass == evaluator_pass:
            overall_matches += 1

        evaluator_issue_types = {
            issue.get("type") for issue in (evaluation.issues_detected or [])
        }

        for name, score in (evaluation.evaluator_scores or {}).items():
            ev_pass = score is not None and score >= _PASS_THRESHOLD
            if human_pass and ev_pass:
                ev_stats[name]["tp"] += 1
            elif not human_pass and not ev_pass:
                ev_stats[name]["tn"] += 1
            elif not human_pass and ev_pass:
                ev_stats[name]["fn"] += 1  # missed issue human caught
            else:
                ev_stats[name]["fp"] += 1  # flagged when human was fine

        for atype in annotation_types:
            human_type_counts[atype] += 1
            if atype in evaluator_issue_types:
                evaluator_caught[atype] += 1

    overall_agreement = round(overall_matches / len(conversations), 3)

    calibration = []
    for name, s in ev_stats.items():
        total = s["tp"] + s["tn"] + s["fp"] + s["fn"]
        agreement_rate = round((s["tp"] + s["tn"]) / total, 3) if total else 0.0
        fpr = round(s["fp"] / (s["fp"] + s["tp"]) if (s["fp"] + s["tp"]) else 0.0, 3)
        fnr = round(s["fn"] / (s["fn"] + s["tn"]) if (s["fn"] + s["tn"]) else 0.0, 3)
        calibration.append({
            "evaluator": name,
            "sample_count": total,
            "agreement_rate": agreement_rate,
            "false_positive_rate": fpr,
            "false_negative_rate": fnr,
        })

    blind_spots = [
        {
            "issue_type": itype,
            "human_flagged_count": count,
            "evaluator_missed_count": count - evaluator_caught.get(itype, 0),
        }
        for itype, count in human_type_counts.most_common()
        if count - evaluator_caught.get(itype, 0) > 0
    ]

    return CalibrationResult(
        conversations_analyzed=len(conversations),
        overall_agreement=overall_agreement,
        evaluator_calibration=calibration,
        blind_spots=blind_spots,
    )
