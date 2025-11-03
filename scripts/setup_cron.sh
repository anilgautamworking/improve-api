#!/bin/bash
# Setup cron job for daily pipeline execution

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Python executable path (adjust if needed)
PYTHON_PATH=$(which python3)

# Pipeline script path
PIPELINE_SCRIPT="$SCRIPT_DIR/run_daily_pipeline.py"

# Log file
LOG_FILE="$PROJECT_DIR/logs/cron.log"

# Cron schedule (default: daily at 6:00 AM IST)
CRON_HOUR=${CRON_HOUR:-6}
CRON_MINUTE=${CRON_MINUTE:-0}

# Create log directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Create cron entry
CRON_ENTRY="$CRON_MINUTE $CRON_HOUR * * * cd $PROJECT_DIR && $PYTHON_PATH $PIPELINE_SCRIPT >> $LOG_FILE 2>&1"

# Check if cron job already exists
EXISTING_CRON=$(crontab -l 2>/dev/null | grep -F "$PIPELINE_SCRIPT")

if [ -z "$EXISTING_CRON" ]; then
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "Cron job added successfully!"
    echo "Schedule: Daily at $CRON_HOUR:$CRON_MINUTE"
    echo "Command: $CRON_ENTRY"
else
    echo "Cron job already exists:"
    echo "$EXISTING_CRON"
fi

# Show current crontab
echo ""
echo "Current crontab:"
crontab -l

