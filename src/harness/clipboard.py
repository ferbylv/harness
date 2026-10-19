from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def sniff_mime(data: bytes) -> str | None:
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 6 and data[:6] in {b"GIF87a", b"GIF89a"}:
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 2 and data[:2] == b"BM":
        return "image/bmp"
    return None


def read_clipboard_image() -> tuple[bytes, str] | None:
    if sys.platform == "darwin":
        return _macos_image()
    if sys.platform.startswith("linux"):
        return _linux_image()
    return None


def image_paths_in_paste(text: str) -> list[Path]:
    lines = [ln.strip().strip("'\"") for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    paths: list[Path] = []
    for raw in lines:
        item = raw
        if item.startswith("file://"):
            item = unquote(item[7:])
        path = Path(item).expanduser()
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            return []
        paths.append(path)
    return paths


def _macos_image() -> tuple[bytes, str] | None:
    dest_dir = Path(tempfile.mkdtemp(prefix="harness-clip-"))
    dest = dest_dir / "clip.png"
    try:
        try:
            result = subprocess.run(
                ["pngpaste", str(dest)],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                got = _load_image_file(dest)
                if got:
                    return got
        except FileNotFoundError:
            pass
        script = (
            f'set p to POSIX file "{dest}"\n'
            "try\n"
            "  set d to (the clipboard as «class PNGf»)\n"
            "on error\n"
            '  return "NO"\n'
            "end try\n"
            "set f to open for access p with write permission\n"
            "set eof f to 0\n"
            "write d to f\n"
            "close access f\n"
            'return "OK"\n'
        )
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "OK" in (result.stdout or ""):
            return _load_image_file(dest)
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        _rm_temp(dest_dir)
    return None


def _linux_image() -> tuple[bytes, str] | None:
    commands = (
        ["wl-paste", "-t", "image/png"],
        ["wl-paste", "-t", "image/jpeg"],
        ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
        ["xclip", "-selection", "clipboard", "-t", "image/jpeg", "-o"],
    )
    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5)
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            continue
        if result.returncode == 0 and result.stdout:
            mime = sniff_mime(result.stdout)
            if mime:
                return result.stdout, mime
    return None


def _load_image_file(path: Path) -> tuple[bytes, str] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    mime = sniff_mime(data)
    if mime:
        return data, mime
    return None


def _rm_temp(folder: Path) -> None:
    try:
        for child in folder.iterdir():
            child.unlink(missing_ok=True)
        folder.rmdir()
    except OSError:
        pass
