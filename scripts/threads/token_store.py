"""Private file storage shared by the stdlib Threads helpers."""

import os
import stat
import tempfile
from pathlib import Path


def atomic_write(path: Path, text: str) -> None:
    """Replace a file only after its mode-600 replacement is fully written."""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".omni-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_token(path: Path) -> str:
    path = path.expanduser().resolve()
    for parent in path.parents:
        if (parent / ".git").exists():
            raise ValueError("token file must be outside any git repo")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "r", encoding="utf-8") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError("token file must be a regular file with mode 600")
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            raise ValueError("token file must belong to the current user")
        token = handle.read().strip()
    if not token:
        raise ValueError("token file is empty")
    return token
