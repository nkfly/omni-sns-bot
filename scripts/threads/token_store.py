"""Private file storage shared by the stdlib Threads helpers.

POSIX (macOS and Linux) keeps mode 600 and owner checks. Windows cannot
represent those bits: os.fchmod is missing before Python 3.13, S_IMODE does
not come back as 0o600, and opening a directory to fsync fails. On Windows
the git-root refusal stays, and the mode/owner checks are skipped.
"""

import os
import stat
import tempfile
from pathlib import Path


def private_mode_enforced() -> bool:
    """True where a mode-600 check is meaningful. False on Windows."""
    return os.name != "nt"


def directory_sync_supported() -> bool:
    """Opening a directory for fsync works on POSIX and fails on Windows."""
    return os.name != "nt"


def suggested_secret_dir() -> Path:
    """A starting directory outside the clone. The caller still checks git.

    Windows has no reliable Unix mode, so this is under the user profile
    (%APPDATA%\\omni-sns-bot) rather than the repository. The scripts do not
    read Windows Credential Manager; an editor who uses it should load the
    secret into the environment for one process without printing it.
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
        return root / "omni-sns-bot"
    return Path.home() / "omni-sns-workspace"


def atomic_write(path: Path, text: str) -> None:
    """Replace a file only after its replacement is fully written.

    On POSIX the replacement is mode 600 before it is visible at `path`.
    On Windows the exclusive temp file is still replaced atomically, without
    fchmod or a directory fsync.
    """
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".omni-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            if private_mode_enforced():
                if hasattr(os, "fchmod"):
                    os.fchmod(handle.fileno(), 0o600)
                else:
                    os.chmod(temporary, 0o600)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sync_directory(path: Path) -> None:
    if not directory_sync_supported():
        return
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
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("token file must be a regular file")
        if private_mode_enforced():
            if stat.S_IMODE(info.st_mode) != 0o600:
                raise ValueError("token file must be a regular file with mode 600")
            if hasattr(os, "getuid") and info.st_uid != os.getuid():
                raise ValueError("token file must belong to the current user")
        token = handle.read().strip()
    if not token:
        raise ValueError("token file is empty")
    return token
