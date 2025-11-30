#!/bin/bash

PORT=$1

if [ -z "$PORT" ]; then
  echo "Usage: ./kill_port.sh <port>"
  exit 1
fi

# Find all PIDs using lsof (may return multiple)
PIDS=$(lsof -ti :$PORT 2>/dev/null)

if [ -n "$PIDS" ]; then
  for PID in $PIDS; do
    echo "Killing PID $PID on port $PORT..."
    kill -9 $PID 2>/dev/null
  done
  # Wait for port to be released (max 3 seconds)
  for i in {1..30}; do
    if ! lsof -ti :$PORT >/dev/null 2>&1; then
      break
    fi
    sleep 0.1
  done
else
  echo "No process found on port $PORT."
fi
