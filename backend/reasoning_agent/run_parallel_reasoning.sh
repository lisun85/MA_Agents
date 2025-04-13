#!/bin/bash

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "../../.venv" ]; then
  source ../../.venv/bin/activate
  echo "Activated virtual environment"
fi

# Run the orchestrator
echo "Starting parallel reasoning orchestrator..."
python -m backend.reasoning_agent.reasoning

# Check the exit code
if [ $? -eq 0 ]; then
  echo "Orchestrator completed successfully!"
else
  echo "Orchestrator failed with an error. Check the logs for details."
fi 