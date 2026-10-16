"""Bounded retries for transient Windows file sharing violations."""
import os
import time


def replace_path(source, target):
    for attempt in range(20):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.05)
