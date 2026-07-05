"""アプリのエントリポイント。"""
from __future__ import annotations

import sys
from pathlib import Path

from . import APP_NAME
from .logging_setup import setup_logging


def _app_icon():
    """ウィンドウアイコンを返す。

    resources/app.ico があればそれを使い、無ければテーマのロゴマークを
    描画して使う（凍結環境でも必ずアイコンが付く）。
    """
    from PySide6.QtGui import QIcon

    candidates = [
        # 開発時: src/imagetopdf/app.py から見たプロジェクトルート。
        Path(__file__).resolve().parents[2] / "resources" / "app.ico",
    ]
    # PyInstaller 凍結時: datas は _MEIPASS（onedir では _internal/）配下に展開される。
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "resources" / "app.ico")
    for path in candidates:
        if path.is_file():
            return QIcon(str(path))

    from .ui.widgets import logo_pixmap

    return QIcon(logo_pixmap(256))


def main() -> int:
    setup_logging()
    # Qt のインポートは setup 後（起動失敗時のログを残すため）。
    from PySide6.QtWidgets import QApplication

    from .ui import theme
    from .ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    theme.apply_theme(app)
    app.setWindowIcon(_app_icon())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
