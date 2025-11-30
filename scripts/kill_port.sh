#!/bin/bash

PORT=$1

if [ -z "$PORT" ]; then
  echo "Usage: ./kill_port.sh <port>"
  exit 1
fi

# Find PID using lsof
PID=$(lsof -ti :$PORT)

if [ -n "$PID" ]; then
  echo "Killing process $PID on port $PORT..."
  kill -9 $PID
else
  echo "No process found on port $PORT."
fi

