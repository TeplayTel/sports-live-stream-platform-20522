#!/bin/bash
cd /home/kavia/workspace/code-generation/sports-live-stream-platform-20522/sports_telecast_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

