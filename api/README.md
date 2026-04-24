# api/

FastAPI backend for SchemaGuard.

## Running

```bash
cd schema-guard-llm-validation
uvicorn api.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service info + endpoint list |
| `GET` | `/health` | Health check with version and supported domains |
| `POST` | `/validate` | Validate a single record (structural + semantic + confidence + decision) |
| `POST` | `/batch-validate` | Validate multiple records with drift detection |
| `POST` | `/generate` | Return sample records from seed data |

## Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app creation, CORS, router mounting |
| `routes.py` | Endpoint handlers — delegates to validator pipeline |
| `models.py` | Pydantic request/response models |

## Example Request

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "healthcare",
    "record": {
      "patient_id": "P-3021",
      "first_name": "James",
      "last_name": "Carter",
      "date_of_birth": "1978-11-02",
      "gender": "male",
      "admission_date": "2024-09-14",
      "discharge_date": "2024-09-19",
      "diagnosis_code": "J18.9",
      "diagnosis_description": "Pneumonia, unspecified organism",
      "treating_physician": "Dr. Susan Park",
      "medication": "Azithromycin",
      "patient_age": 45,
      "emergency_admission": false
    }
  }'
```
