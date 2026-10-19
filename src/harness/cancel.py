from __future__ import annotations

import os
import signal
import subprocess
import threading
from collections.abc import Callable


class Cancelled(Exception):
    """The user aborted the current turn."""


class CancelToken:
    def __init__(self) -> None:
        self._event = threading.Event()
        self._proc: subprocess.Popen | None = None
        self._close: Callable[[], None] | None = None
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._event.clear()
            self._proc = None
            self._close = None

    def is_set(self) -> bool:
        return self._event.is_set()

    def throw_if_set(self) -> None:
        if self._event.is_set():
            raise Cancelled()

    def cancel(self) -> None:
        self._event.set()
        with self._lock:
            proc = self._proc
            closer = self._close
        if proc is not None and proc.poll() is None:
            _kill_proc(proc)
        if closer is not None:
            try:
                closer()
            except Exception:
                pass

    def set_process(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._proc = proc
        if self._event.is_set():
            _kill_proc(proc)

    def set_close(self, closer: Callable[[], None]) -> None:
        with self._lock:
            self._close = closer
        if self._event.is_set():
            try:
                closer()
            except Exception:
                pass


def _kill_proc(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            pass
