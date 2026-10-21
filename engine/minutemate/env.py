"""Process-level environment preparation (CUDA DLLs on Windows)."""

from __future__ import annotations

import os
import site
import sys
from pathlib import Path

_configured = False
_cuda_devices: int | None = None


def setup_windows_cuda() -> None:
    global _configured
    if _configured or sys.platform != "win32":
        _configured = True
        return

    candidates: list[Path] = [
        Path(sys.prefix) / "Lib" / "site-packages" / "nvidia",
    ]
    if getattr(sys, "frozen", False):
        candidates.append(Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "nvidia")
        candidates.append(Path(sys.executable).parent / "nvidia")

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
    global _cuda_devices
    if _cuda_devices is not None:
        return _cuda_devices
    try:
        setup_windows_cuda()
        import ctranslate2

        count = int(ctranslate2.get_cuda_device_count())
        if count <= 0:
            _cuda_devices = 0
            return 0
        try:
            usable = bool(ctranslate2.get_supported_compute_types("cuda"))
        except Exception:
            usable = False
        _cuda_devices = count if usable else 0
        return _cuda_devices
    except Exception:
        _cuda_devices = 0
        return 0
