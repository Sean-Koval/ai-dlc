"""Cross-process coordination for project-owned writes."""

from __future__ import annotations

import fcntl
import hashlib
import os
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_PROCESS_LOCK = threading.RLock()
_LOCAL = threading.local()


@contextmanager
def project_write_lock(root: Path) -> Iterator[None]:
    """Serialize AI-DLC writes for one project, with same-thread reentrancy."""
    resolved = Path(root).resolve()
    key = hashlib.sha256(str(resolved).encode()).hexdigest()
    depths = getattr(_LOCAL, "depths", None)
    if depths is None:
        depths = {}
        _LOCAL.depths = depths

    with _PROCESS_LOCK:
        if depths.get(key, 0):
            depths[key] += 1
            try:
                yield
            finally:
                depths[key] -= 1
            return

        lock_root = Path(tempfile.gettempdir()) / f"ai-dlc-project-locks-{os.getuid()}"
        lock_root.mkdir(mode=0o700, exist_ok=True)
        with (lock_root / f"{key}.lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            depths[key] = 1
            try:
                yield
            finally:
                depths.pop(key, None)
                fcntl.flock(stream, fcntl.LOCK_UN)
