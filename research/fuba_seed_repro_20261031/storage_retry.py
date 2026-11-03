"""Bounded Windows sharing-violation retry; never changes payload contents."""
import os
import time


def replace_with_retry(source, target, *, attempts=40, delay=.05):
    for attempt in range(attempts):
        try:
            os.replace(source, target)
            return attempt
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)
