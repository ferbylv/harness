from __future__ import annotations

from pathlib import Path


class Workspace:
    """Resolve paths inside the project root. Tools must not escape it."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def resolve(self, path: str) -> Path:
        raw = Path(path).expanduser()
        candidate = raw.resolve() if raw.is_absolute() else (self.root / raw).resolve()
        if not candidate.is_relative_to(self.root):
            raise PermissionError(f"path escapes workspace: {path}")
        return candidate

    def rel(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.root))
