# data_gen/

Synthetic data generation pipeline for SchemaGuard.

## Structure

```
data_gen/
├── README.md                  # This file
├── prompt_strategy.md         # Prompting approach and design rationale
├── dataset_spec.md            # Dataset format, sizes, labeling schema
├── generate_dataset.py        # Generation script (scaffolding)
├── data_plan.md               # High-level data generation plan
├── prompts/
│   ├── healthcare_valid.md
│   ├── healthcare_invalid.md
│   ├── healthcare_edge_cases.md
│   ├── finance_valid.md
│   ├── finance_invalid.md
│   ├── finance_edge_cases.md
│   └── explanation_prompts.md
├── sample_data/
│   ├── healthcare_seed_examples.json
│   └── finance_seed_examples.json
└── datasets/
    ├── raw/
    └── labeled/
```

## Generating Data

```bash
# Generate valid healthcare records
python generate_dataset.py --domain healthcare_intake --category valid --count 10

# Generate invalid records targeting a specific rule
python generate_dataset.py --domain financial_loan_application --category invalid --count 5 --rule FN-002

# Generate edge cases
python generate_dataset.py --domain healthcare_intake --category edge_case --count 5
```

LLM provider integration is not yet connected. The script structure is ready — plug in your API key and provider in `.env` to start generating.

## Seed Data

`sample_data/` contains hand-written examples (3 valid, 3 invalid, 2 edge-case per domain) that serve as ground truth references for testing the validation pipeline before LLM-generated data is available.
