# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

for package in (
    "minutemate",
    "faster_whisper",
    "ctranslate2",
    "sherpa_onnx",
    "onnxruntime",
    "tokenizers",
    "huggingface_hub",
    "av",
    "scipy",
    "numpy",
):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

_GPU_ONLY = (
    "onnxruntime_providers_cuda",
    "onnxruntime_providers_tensorrt",
    "onnxruntime_providers_dml",
    "directml.dll",
)


def _cpu_only(entries):
    kept = []
    for entry in entries:
        dest = str(entry[1]).replace("\\", "/").lower()
        if any(marker in dest for marker in _GPU_ONLY):
            continue
        kept.append(entry)
    return kept


binaries = _cpu_only(binaries)
datas = _cpu_only(datas)

a = Analysis(
    ["packaging/engine_entry.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "pytest",
        "PyInstaller",
        "pyarrow",
        "IPython",
        "notebook",
        "torch",
        "transformers",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="minutemate-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="minutemate-engine",
)
