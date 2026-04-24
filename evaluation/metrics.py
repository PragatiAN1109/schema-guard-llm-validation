"""
SchemaGuard — Evaluation Metrics

Computes precision, recall, false-quarantine rate, and confidence
separation from evaluation results.
"""


def compute_metrics(results: list[dict]) -> dict:
    """
    Compute evaluation metrics from a list of per-record eval results.

    Each result has:
        - expected_semantic_valid: bool
        - actual_semantic_valid: bool
        - confidence_score: float
        - decision: str
        - category: str
    """
    tp = fp = tn = fn = 0
    false_quarantine = 0
    valid_scores = []
    invalid_scores = []

    for r in results:
        expected = r["expected_semantic_valid"]
        actual = r["actual_semantic_valid"]

        if expected and actual:
            tn += 1  # true negative (correctly passed valid record)
        elif expected and not actual:
            fp += 1  # false positive (incorrectly flagged a valid record)
        elif not expected and not actual:
            tp += 1  # true positive (correctly caught invalid record)
        elif not expected and actual:
            fn += 1  # false negative (missed an invalid record)

        # False quarantine: valid record routed to quarantined
        if expected and r["decision"] == "quarantined":
            false_quarantine += 1

        # Confidence separation
        if expected:
            valid_scores.append(r["confidence_score"])
        else:
            invalid_scores.append(r["confidence_score"])

    total = len(results)
    total_valid = tn + fp
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fqr = false_quarantine / total_valid if total_valid > 0 else 0.0

    return {
        "total_records": total,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_quarantine_rate": round(fqr, 4),
        "mean_confidence_valid": round(sum(valid_scores) / len(valid_scores), 4) if valid_scores else None,
        "mean_confidence_invalid": round(sum(invalid_scores) / len(invalid_scores), 4) if invalid_scores else None,
        "accuracy": round((tp + tn) / total, 4) if total > 0 else 0.0,
    }


def print_report(domain: str, metrics: dict) -> None:
    """Print a formatted evaluation report."""
    print(f"\n  Domain:              {domain}")
    print(f"  Total records:       {metrics['total_records']}")
    print(f"  TP / FP / TN / FN:  {metrics['true_positives']} / {metrics['false_positives']} / {metrics['true_negatives']} / {metrics['false_negatives']}")
    print(f"  Precision:           {metrics['precision']}")
    print(f"  Recall:              {metrics['recall']}")
    print(f"  F1 Score:            {metrics['f1_score']}")
    print(f"  False quarantine:    {metrics['false_quarantine_rate']}")
    print(f"  Avg confidence (valid):   {metrics['mean_confidence_valid']}")
    print(f"  Avg confidence (invalid): {metrics['mean_confidence_invalid']}")
    print(f"  Accuracy:            {metrics['accuracy']}")
