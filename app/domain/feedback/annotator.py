from collections import Counter


def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float | None:
    if len(labels_a) != len(labels_b) or not labels_a:
        return None

    total = len(labels_a)
    observed_agreement = sum(a == b for a, b in zip(labels_a, labels_b)) / total

    all_labels = labels_a + labels_b
    counts = Counter(all_labels)
    expected_agreement = sum((counts[k] / (2 * total)) ** 2 for k in counts)

    if expected_agreement == 1.0:
        return 1.0

    return round((observed_agreement - expected_agreement) / (1 - expected_agreement), 3)


def kappa_to_level(kappa: float | None) -> str:
    if kappa is None:
        return "poor"
    if kappa >= 0.81:
        return "perfect"
    if kappa >= 0.61:
        return "strong"
    if kappa >= 0.41:
        return "moderate"
    if kappa >= 0.21:
        return "fair"
    return "poor"


def routing_decision(kappa: float | None, threshold: float, avg_confidence: float = 1.0) -> str:
    if kappa is not None and kappa >= threshold and avg_confidence >= 0.6:
        return "auto_label"
    return "human_review"
