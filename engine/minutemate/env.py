"""Process-level environment preparation (CUDA DLLs on Windows)."""

from __future__ import annotations

import os
import site
import sys
from pathlib import Path

_configured = False


def setup_windows_cuda() -> None:
    global _configured
    if _configured or sys.platform != "win32":
        _configured = True
        return

    candidates: list[Path] = [
        Path(sys.prefix) / "Lib" / "site-packages" / "nvidia",
        Path(sys.prefix) / "Lib" / "site-packages" / "nvidia",
    ]

    try:
        for entry in site.getsitepackages():
            candidates.append(Path(entry) / "nvidia")
    except Exception:
        pass

    for base in candidates:
        if not base.exists():
            continue
        for bin_dir in base.glob("*/bin"):
            try:
                resolved = bin_dir.resolve()
                os.add_dll_directory(str(resolved))
                os.environ["PATH"] = str(resolved) + os.pathsep + os.environ.get("PATH", "")
            except Exception:
                continue

    _configured = True


def cuda_device_count() -> int:
    try:
        import ctranslate2

        return int(ctranslate2.get_cuda_device_count())
    except Exception:
        return 0
