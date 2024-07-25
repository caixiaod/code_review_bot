#!/bin/bash

# Define the name of your Python script
SCRIPT_NAME="code_review_service.py"

# Find the PID of the running script
PID=$(pgrep -f $SCRIPT_NAME)

# Check if the script is running
if [ -z "$PID" ]; then
  echo "No running process found for $SCRIPT_NAME."
else
  echo "Found running process $SCRIPT_NAME with PID $PID. Killing the process..."
  
  # Kill the process
  kill $PID
  
  # Wait for a moment to ensure the process is terminated
  sleep 2
  
  # Verify if the process is killed
  if ps -p $PID > /dev/null; then
    echo "Failed to kill the process $PID. Force killing..."
    kill -9 $PID
  else
    echo "Process $PID successfully killed."
  fi
fi

# Restart the Python script with nohup
echo "Restarting $SCRIPT_NAME..."
nohup python $SCRIPT_NAME &

# Get the new PID of the started process
NEW_PID=$(pgrep -f $SCRIPT_NAME)

# Check if the new process started successfully
if [ -z "$NEW_PID" ]; then
  echo "Failed to start $SCRIPT_NAME."
else
  echo "$SCRIPT_NAME started successfully with PID $NEW_PID."
fi
