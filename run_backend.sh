#!/bin/bash
# Start SchemaGuard API server
# Usage: ./run_backend.sh

cd "$(dirname "$0")"
echo "Starting SchemaGuard API on http://localhost:8000"
echo "Swagger docs: http://localhost:8000/docs"
echo ""
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
