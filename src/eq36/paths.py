import sys
from pathlib import Path

def get_bin() -> Path:
    binpath = (Path(__file__).parent / "bin").resolve()
    if not binpath.is_dir():
        msg = f"{binpath} is not a directory"
        raise Exception(msg)
    return binpath


def get_execpath(cmd: str | Path) -> Path:
    suffix = ".exe" if sys.platform.startswith("win") and not str(cmd).endswith(".exe") else ""
    execpath = (get_bin() / (str(cmd) + suffix)).resolve()
    if not execpath.is_file():
        msg = f"{execpath!s} command not found"
        raise Exception(msg)
    return execpath

__all__ = [
    "get_bin",
    "get_execpath"
]
