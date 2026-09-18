"""Timestamped stdout printing for [APP-DEBUG] lines.

The ``log.info()`` copies of these messages get timestamps from the app
logger; the ``print()`` copies land on container stdout with no context, so
route stdout debug output through ``debug_print``. Emitting both is
deliberate: the app log is the durable record, stdout is what you see when
tailing the service container.
"""

# standard library
from datetime import datetime, timezone


def debug_print(msg: str) -> None:
    """Print msg to stdout prefixed with a UTC timestamp."""
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    print(f'{ts} {msg}', flush=True)
