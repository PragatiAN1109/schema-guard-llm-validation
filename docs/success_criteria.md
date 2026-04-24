# Success Criteria

Target criteria for evaluating the completed system. These are goals, not claimed results.

## Structural Validation
- Schema validator correctly identifies all structural violations in the evaluation dataset
- Target: 100% accuracy on designed structural test cases (deterministic checks)

## Semantic Rule Engine
- Detects labeled silent-failure records in the evaluation dataset
- Target: precision ≥ 0.90, recall ≥ 0.85 on the silent-failure subset

## Drift Detection
- Flags simulated distribution shifts (mean shift ≥ 2 std dev, categorical frequency change ≥ 20%)
- False alert rate on stable batches < 10%

## Confidence Scoring
- Valid records score significantly higher than silent-failure records (non-overlapping IQRs)
- Quarantine threshold routes ≥ 80% of known silent-failure records to flagged or quarantined

## End-to-End Flow
- Every processed record receives a routing decision (trusted / flagged / quarantined)
- Flagged and quarantined records include a human-readable explanation
- Every validation run produces an audit log entry with full trace

## Demo UI
- Single-record validation works for both domains
- User can input JSON, select a domain, and receive structural result, semantic result, confidence score, routing decision, and explanation

## Evaluation Datasets
- At least 250 labeled records per domain
- Manually verified subset of 50+ records per domain confirms label accuracy

## Repository
- Clean structure, documented setup, reproducible from a fresh clone
