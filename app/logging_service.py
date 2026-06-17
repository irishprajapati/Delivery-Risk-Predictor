import json
from datetime import datetime
import os

LOG_FILE = "prediction_logs.json"


def save_log(data: dict):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        **data
    }

    # If file doesn't exist, create it
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f)

    # Read existing logs
    with open(LOG_FILE, "r") as f:
        logs = json.load(f)

    # Append new log
    logs.append(log_entry)

    # Save back
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)