from collections import defaultdict
import time

FAILED_ATTEMPTS = defaultdict(list)

MAX_ATTEMPTS = 5
BLOCK_TIME = 300  # seconds (5 min)

def is_blocked(username: str):
    attempts = FAILED_ATTEMPTS[username]

    # remove old attempts
    FAILED_ATTEMPTS[username] = [
        t for t in attempts if time.time() - t < BLOCK_TIME
    ]

    return len(FAILED_ATTEMPTS[username]) >= MAX_ATTEMPTS

def record_failure(username: str):
    FAILED_ATTEMPTS[username].append(time.time())

def clear_failures(username: str):
    FAILED_ATTEMPTS.pop(username, None)