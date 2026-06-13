"""
trace.py

One-line-per-event console logging for the human-test session. Off by
default so pytest stays quiet. Turn it on for a run with:

    FITFINDR_LOG=1 python app.py
    FITFINDR_LOG=1 python agent.py

Every LLM call, tool call, and file read/write emits a single line to
stderr, timestamped to the millisecond, so the terminal shows the whole
interaction as a live stream. Long values are truncated.
"""
import os
import sys
import time

_ENABLED = os.environ.get("FITFINDR_LOG", "").lower() not in ("", "0", "false", "no")


def enabled() -> bool:
    return _ENABLED


def log(message: str) -> None:
    """Emit one timestamped line to stderr. No-op when logging is off."""
    if not _ENABLED:
        return
    now = time.time()
    stamp = time.strftime("%H:%M:%S", time.localtime(now))
    millis = int((now - int(now)) * 1000)
    print(f"{stamp}.{millis:03d} {message}", file=sys.stderr, flush=True)


def trunc(value, limit: int = 90) -> str:
    """Collapse to a single line and cut to `limit` chars for log output."""
    text = str(value).replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "..."
