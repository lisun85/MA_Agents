#!/bin/bash

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "./.venv" ]; then
  source ./.venv/bin/activate
  echo "Activated virtual environment"
fi

# Run the graph workflow
echo "Starting DeepSeek reasoning orchestration with LangGraph..."
python -m backend.graph

# Check exit code
if [ $? -eq 0 ]; then
  echo "Orchestration completed successfully!"
else
  echo "Orchestration failed. Check the logs for details."
fi 