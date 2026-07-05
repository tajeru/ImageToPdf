# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 仕様ファイル。

ビルド:
    cd ImageToPDF
    pyinstaller build/imagetopdf.spec --noconfirm

成果物: dist/ImageToPDF/ImageToPDF.exe （onedir 形式）
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# このファイルは build/ にあるので、プロジェクトルートは1つ上。
ROOT = Path(SPECPATH).resolve().parent
ICON = ROOT / "resources" / "app.ico"

hiddenimports = []
# img2pdf / Pillow のプラグインを取りこぼさない。
hiddenimports += collect_submodules("PIL")

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    # ウィンドウアイコン用に resources/ を同梱（無ければ描画ロゴにフォールバック）。
    datas=[(str(ICON), "resources")] if ICON.exists() else [],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # 使わない重い Qt モジュールを除外して配布サイズを抑える。
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.Qt3DCore",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtNetwork",
        "PySide6.QtPdf",
        "PySide6.QtCharts",
        "tkinter",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImageToPDF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # ウィンドウアプリ（コンソール非表示）
    icon=str(ICON) if ICON.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ImageToPDF",
)
