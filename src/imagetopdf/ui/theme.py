"""アプリ全体のビジュアルテーマ（デザイントークン + QSS + 適用ヘルパー）。

見た目に関する定義はこのモジュールに一元化する（技術指示書 §4.1 の「スタイル」）。
カラー・フォントなどのトークンを変更すれば全画面へ反映される。
QSS で表現しきれない装飾（ドロップ領域の枠線グロー、ロゴマーク等）は
ui/widgets.py がここのトークンを参照して QPainter で描画する。
"""
from __future__ import annotations

import sys
from string import Template

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget

# --- カラートークン（ダーク基調 + オーロラグラデーション） --------------------
BG = "#0C1017"            # ウィンドウ背景（最深部）
SURFACE = "#141A24"       # カード面
SURFACE2 = "#1B2330"      # 入力欄・既定ボタン面
HOVER = "#232D3D"         # ホバー面 / ポップアップ面
WELL = "#0A0E15"          # 沈み込み面（セグメント台座・進捗バー溝）
BORDER = "#2A3444"        # 標準ボーダー
BORDER_SOFT = "#1E2734"   # 弱いボーダー（カード輪郭）
DASH = "#3D4C63"          # 破線・ホバー時ボーダー

TEXT = "#E9EEF6"          # 主文字
SUB = "#9BA8BA"           # 補助文字
FAINT = "#5F6D80"         # 弱い文字（ヒント・無効）

ACCENT = "#7C6AF2"        # 藍（グラデ始点）
ACCENT2 = "#AE5FF2"       # 紫（グラデ中間）
ACCENT3 = "#F2679C"       # ローズ（グラデ終点）
OK = "#3ED598"
ERR = "#F2707E"

FONT_FAMILIES = ["Yu Gothic UI", "Segoe UI Variable Text", "Segoe UI", "Meiryo UI"]
FONT_POINT_SIZE = 10


def blend(base: str | QColor, over: str | QColor, t: float) -> QColor:
    """2色を t（0.0〜1.0）で線形補間した QColor を返す。"""
    a, b = QColor(base), QColor(over)
    t = max(0.0, min(1.0, t))
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    )


def repolish(widget: QWidget) -> None:
    """動的プロパティ（state 等）変更後に QSS を再評価させる。"""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def enable_dark_title_bar(window: QWidget) -> None:
    """Windows のネイティブタイトルバーをダーク表示にする（非対応環境は無視）。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(window.winId())
        value = ctypes.c_int(1)
        # DWMWA_USE_IMMERSIVE_DARK_MODE は 20（Win10 の旧ビルドでは 19）。
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)
            ) == 0:
                return
    except Exception:
        pass


def apply_theme(app: QApplication) -> None:
    """Fusion スタイル + ダークパレット + QSS + フォントを適用する。"""
    app.setStyle("Fusion")

    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPointSize(FONT_POINT_SIZE)
    app.setFont(font)

    app.setPalette(_palette())
    app.setStyleSheet(stylesheet())


def _palette() -> QPalette:
    """QSS が及ばないネイティブ部品（コンボの矢印等）用のダークパレット。"""
    pal = QPalette()
    c = QColor
    pal.setColor(QPalette.Window, c(BG))
    pal.setColor(QPalette.WindowText, c(TEXT))
    pal.setColor(QPalette.Base, c(SURFACE2))
    pal.setColor(QPalette.AlternateBase, c(SURFACE))
    pal.setColor(QPalette.Text, c(TEXT))
    pal.setColor(QPalette.Button, c(SURFACE2))
    pal.setColor(QPalette.ButtonText, c(TEXT))
    pal.setColor(QPalette.BrightText, c("#FFFFFF"))
    pal.setColor(QPalette.Highlight, c(ACCENT))
    pal.setColor(QPalette.HighlightedText, c("#FFFFFF"))
    pal.setColor(QPalette.ToolTipBase, c(HOVER))
    pal.setColor(QPalette.ToolTipText, c(TEXT))
    pal.setColor(QPalette.PlaceholderText, c(FAINT))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, c(FAINT))
    pal.setColor(QPalette.Disabled, QPalette.Highlight, c(BORDER))
    return pal


def stylesheet() -> str:
    return _QSS.substitute(
        bg=BG,
        surface=SURFACE,
        surface2=SURFACE2,
        hover=HOVER,
        well=WELL,
        border=BORDER,
        border_soft=BORDER_SOFT,
        dash=DASH,
        text=TEXT,
        sub=SUB,
        faint=FAINT,
        accent=ACCENT,
        accent2=ACCENT2,
        accent3=ACCENT3,
        ok=OK,
        err=ERR,
    )


# 注意: rgba() のアルファは 0〜255 で書く（Template の $ 置換と % 表記の衝突回避）。
_QSS = Template("""
* { outline: 0; }

#window { background: $bg; }
QWidget { color: $text; }
QLabel { background: transparent; }

/* --- 見出し・テキスト ------------------------------------------------- */
QLabel[cls="h1"] { font-size: 16pt; font-weight: 800; }
QLabel[cls="tagline"] { color: $sub; font-size: 9.5pt; }
QLabel[cls="chip"] {
    color: #CDC3FF;
    background: rgba(124, 106, 242, 31);
    border: 1px solid rgba(124, 106, 242, 84);
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 8pt;
    font-weight: 700;
}
QLabel[cls="field"] { color: $sub; font-size: 9pt; font-weight: 700; }
QLabel[cls="hint"] { color: $faint; font-size: 8.5pt; }
QLabel[cls="status"] { color: $sub; font-size: 9.5pt; }
QLabel[cls="status"][state="ok"] { color: $ok; }
QLabel[cls="status"][state="error"] { color: $err; }

/* --- ドロップ領域内のテキスト ------------------------------------------ */
QLabel[cls="dropTitle"] { color: $text; font-size: 12.5pt; font-weight: 700; }
QLabel[cls="dropSub"] { color: $sub; font-size: 9pt; }
QLabel[cls="dropMeta"] { color: $faint; font-size: 8pt; font-weight: 600; }
QLabel[cls="dropTitle"]:disabled,
QLabel[cls="dropSub"]:disabled,
QLabel[cls="dropMeta"]:disabled { color: $faint; }

/* --- カード / セグメント台座 ------------------------------------------- */
QFrame[cls="card"] {
    background: $surface;
    border: 1px solid $border_soft;
    border-radius: 16px;
}
QFrame[cls="segmented"] {
    background: $well;
    border: 1px solid $border_soft;
    border-radius: 10px;
}

/* --- ボタン ------------------------------------------------------------ */
QPushButton {
    background: $surface2;
    color: $text;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 6px 14px;
}
QPushButton:hover { background: $hover; }
QPushButton:disabled { color: $faint; background: $well; border-color: $border_soft; }

QPushButton[cls="segment"] {
    background: transparent;
    color: $sub;
    border: none;
    border-radius: 7px;
    padding: 5px 14px;
    font-weight: 600;
}
QPushButton[cls="segment"]:hover { color: $text; }
QPushButton[cls="segment"]:checked {
    color: #FFFFFF;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 $accent, stop:0.55 $accent2, stop:1 $accent3);
}
QPushButton[cls="segment"]:disabled { color: $faint; }
QPushButton[cls="segment"]:checked:disabled { background: $hover; color: $sub; }

QPushButton[cls="primary"] {
    color: #FFFFFF;
    font-weight: 700;
    border: none;
    border-radius: 10px;
    padding: 10px 30px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 $accent, stop:0.55 $accent2, stop:1 $accent3);
}
QPushButton[cls="primary"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #8F7EFF, stop:0.55 #BE73FF, stop:1 #FF7FAF);
}
QPushButton[cls="primary"]:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6A59DB, stop:0.55 #964FD6, stop:1 #D55688);
}
QPushButton[cls="primary"]:disabled { background: $well; color: $faint; }

QPushButton[cls="ghost"] {
    background: transparent;
    color: $sub;
    border: 1px solid $border;
    border-radius: 10px;
    padding: 9px 18px;
    font-weight: 600;
}
QPushButton[cls="ghost"]:hover { color: $text; border-color: $accent; }
QPushButton[cls="ghost"]:disabled {
    color: $faint;
    border-color: $border_soft;
    background: transparent;
}

QPushButton[cls="ghostSmall"] {
    background: transparent;
    color: $sub;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 5px 12px;
}
QPushButton[cls="ghostSmall"]:hover { color: $text; border-color: $accent; }
QPushButton[cls="ghostSmall"]:disabled {
    color: $faint;
    border-color: $border_soft;
    background: transparent;
}

/* --- 入力（スピン / コンボ） -------------------------------------------- */
QSpinBox {
    background: $surface2;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 5px 6px 5px 10px;
    selection-background-color: $accent;
}
QSpinBox:hover { border-color: $dash; }
QSpinBox:focus { border-color: $accent; }
QSpinBox:disabled { color: $faint; background: $well; border-color: $border_soft; }
QSpinBox::up-button, QSpinBox::down-button {
    width: 18px;
    border: none;
    background: transparent;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: rgba(255, 255, 255, 16);
    border-radius: 4px;
}

QComboBox {
    background: $surface2;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 5px 10px;
}
QComboBox:hover { border-color: $dash; }
QComboBox:focus { border-color: $accent; }
QComboBox:disabled { color: $faint; background: $well; border-color: $border_soft; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: $hover;
    color: $text;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: rgba(124, 106, 242, 92);
    selection-color: #FFFFFF;
}

/* --- 進捗 --------------------------------------------------------------- */
QProgressBar {
    background: $well;
    border: none;
    border-radius: 4px;
}
QProgressBar::chunk {
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 $accent, stop:0.5 $accent2, stop:1 $accent3);
}

/* --- ダイアログ / ツールチップ ------------------------------------------ */
QMessageBox { background: $surface; }
QMessageBox QLabel { font-size: 10pt; }
QMessageBox QPushButton { min-width: 88px; }

QToolTip {
    background: $hover;
    color: $text;
    border: 1px solid $border;
    padding: 4px 8px;
}
""")
