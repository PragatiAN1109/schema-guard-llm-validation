#!/bin/bash
# Start SchemaGuard Streamlit UI
# Usage: ./run_ui.sh

cd "$(dirname "$0")"
echo "Starting SchemaGuard UI on http://localhost:8501"
echo ""
streamlit run ui/app.py --server.port 8501
