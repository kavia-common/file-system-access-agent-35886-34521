import base64
import os
import shutil
from pathlib import Path
from typing import Tuple


# PUBLIC_INTERFACE
def resolve_safe_path(base_dir: Path, input_path: str) -> Path:
    """Resolve a user provided path safely under a base directory.

    The function allows:
    - Absolute paths (treated as-is) BUT still enforced not to traverse outside base_dir if base_dir is set.
    - Relative paths (resolved from base_dir).

    If base_dir is None-like, we fallback to the current working directory.

    Raises:
        ValueError: If the resolved path escapes the base directory.
    """
    # If base_dir is not provided, use CWD to constrain access
    root = Path(base_dir or os.getcwd()).resolve()

    p = Path(input_path)
    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()

    try:
        p.relative_to(root)
    except Exception as exc:
        # Prevent path traversal outside the allowed root
        raise ValueError(f"Path escapes base directory: {p}") from exc
    return p


# PUBLIC_INTERFACE
def encode_content(data: bytes, encoding: str) -> str:
    """Encode raw bytes to string representation based on encoding."""
    if encoding == "utf-8":
        return data.decode("utf-8")
    if encoding == "latin-1":
        return data.decode("latin-1")
    if encoding == "base64":
        return base64.b64encode(data).decode("ascii")
    if encoding == "binary":
        # Represent as base64 string for transport, but mark via binary flag by caller
        return base64.b64encode(data).decode("ascii")
    raise ValueError(f"Unsupported encoding: {encoding}")


# PUBLIC_INTERFACE
def decode_content(text: str, encoding: str) -> bytes:
    """Decode text to raw bytes based on encoding."""
    if encoding == "utf-8":
        return text.encode("utf-8")
    if encoding == "latin-1":
        return text.encode("latin-1")
    if encoding == "base64" or encoding == "binary":
        return base64.b64decode(text)
    raise ValueError(f"Unsupported encoding: {encoding}")


# PUBLIC_INTERFACE
def copy_or_move(src: Path, dst: Path, is_move: bool, overwrite: bool) -> Tuple[Path, bool]:
    """Copy or move path to destination.

    Returns:
        (result_path, overwritten)
    """
    overwritten = False
    if dst.exists():
        if overwrite:
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink()
            overwritten = True
        else:
            raise FileExistsError(f"Destination exists: {dst}")

    if is_move:
        shutil.move(str(src), str(dst))
    else:
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    return dst, overwritten


# PUBLIC_INTERFACE
def ensure_parent_dir(path: Path) -> None:
    """Ensure parent directory exists for a file path."""
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
