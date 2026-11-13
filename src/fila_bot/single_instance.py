"""Deprecated compatibility shim for the OS-backed per-EVE-client lock.

Legacy ``acquire(reason)`` callers are routed to ``runtime_lock``; this module
never kills another process or treats a PID file as proof of ownership.
"""
from __future__ import annotations

import atexit
import os

from . import runtime_lock
from .win import find_client_window

_OWNER = None


def acquire(reason: str = ""):
    """Acquire the current EVE client's OS lock; never kill a PID from a file."""
    del reason  # preserved only for source compatibility
    global _OWNER
    if _OWNER is not None:
        return _OWNER
    win = find_client_window()
    pid = win.get("pid") if isinstance(win, dict) else None
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        raise RuntimeError("cannot acquire client ownership without a live EVE window PID")
    _OWNER = runtime_lock.acquire(
        pid, client_id=f"eve-pid-{pid}", owner_pid=os.getpid())
    atexit.register(release)
    return _OWNER


def release() -> None:
    """Release this process's OS lock."""
    global _OWNER
    if _OWNER is not None:
        _OWNER.close()
        _OWNER = None
