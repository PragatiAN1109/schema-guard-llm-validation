# scoring/

Confidence scoring and decision routing for SchemaGuard.

## Files

| File | Purpose |
|------|---------|
| `confidence.py` | Base confidence scorer. Used by the single-record pipeline. Structural failure → 0.0, semantic violations reduce by severity weight. |
| `confidence_score.py` | Enhanced scorer with drift-awareness and detailed breakdown. Returns score + breakdown dict showing each penalty component. |
| `router.py` | Base routing logic. Used by the single-record pipeline. |
| `decision.py` | Enhanced decision router with reasoning. Returns decision + reason + thresholds. Critical violations with sub-trusted confidence → quarantined. |

## Confidence Scoring Logic

Start at 1.0, then subtract:

| Condition | Penalty |
|-----------|---------|
| Structural failure | → 0.0 immediately |
| Critical semantic violation | -0.30 per violation |
| Warning semantic violation | -0.12 per violation |
| Info semantic violation | -0.05 per violation |
| Drift alert (batch mode) | -0.03 per alert (max -0.15) |
| No semantic rules evaluated | -0.05 |

## Decision Routing

| Decision | Condition |
|----------|-----------|
| `trusted` | confidence ≥ 0.85 AND all checks pass |
| `flagged` | 0.50 ≤ confidence < 0.85 OR non-critical violations at high confidence |
| `quarantined` | confidence < 0.50 OR structural failure OR critical violation with sub-trusted confidence |

Thresholds are configurable via `CONFIDENCE_TRUSTED_THRESHOLD` and `CONFIDENCE_QUARANTINE_THRESHOLD` environment variables.

## Usage

```python
# Enhanced (with breakdown)
from scoring import compute_confidence_score, make_decision

score_result = compute_confidence_score(structural, semantic, drift_report)
decision_result = make_decision(
    score_result["confidence_score"],
    structural["valid"], semantic["valid"],
    semantic["violations"]
)
# decision_result["decision"] -> "trusted" | "flagged" | "quarantined"
# decision_result["reason"] -> "All checks passed"
```
