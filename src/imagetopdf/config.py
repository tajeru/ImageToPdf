"""アプリ全体で使う既定値・設定（ConvertOptions）・設定の保存/読込。

GUI 非依存。core からも GUI からも参照する。
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from . import APP_NAME

# --- 対応する入力画像形式（小文字・ドット付き） -------------------------------
# HEIC/AVIF/GIF は初版では非対応（技術指示書 §2）。
SUPPORTED_EXTS: frozenset[str] = frozenset({".webp", ".png", ".jpg", ".jpeg"})

# --- アップデート確認先（GitHub Releases） ---------------------------------
GITHUB_REPO = "tajeru/ImageToPdf"

# --- DPI -----------------------------------------------------------------
DEFAULT_DPI = 300
MIN_DPI = 72
MAX_DPI = 1200

# --- 用紙サイズ（mm, portrait 基準） --------------------------------------
PAPER_SIZES_MM: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "A5": (148.0, 210.0),
    "B5": (176.0, 250.0),
    "Letter": (215.9, 279.4),
}
DEFAULT_PAPER = "A4"


class ConvertMode(str, Enum):
    """変換モード。"""

    SINGLE = "single"        # 1フォルダ → 1PDF（選択フォルダ直下の画像）
    SUBFOLDERS = "subfolders"  # 画像のみのサブフォルダごとに1PDF


class PageMode(str, Enum):
    """ページサイズの扱い。"""

    ORIGINAL = "original"  # 画像そのまま（画素数 ÷ DPI＝物理サイズ）
    FIXED = "fixed"        # 用紙サイズに統一（A4 等）


class Orientation(str, Enum):
    """FIXED 時のページ向き。"""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    AUTO = "auto"  # 画像の縦横で自動回転


@dataclass
class ConvertOptions:
    """1回の変換ジョブのオプション。"""

    mode: ConvertMode = ConvertMode.SINGLE
    dpi: int = DEFAULT_DPI
    page_mode: PageMode = PageMode.ORIGINAL
    paper: str = DEFAULT_PAPER
    orientation: Orientation = Orientation.PORTRAIT
    # None の場合は「入力フォルダと同じ階層」に出力する。
    output_dir: Path | None = None

    def validated(self) -> "ConvertOptions":
        """値域チェックして正規化した複製を返す。"""
        dpi = int(self.dpi)
        if dpi < MIN_DPI or dpi > MAX_DPI:
            raise ValueError(f"DPI は {MIN_DPI}〜{MAX_DPI} の範囲で指定してください（指定値: {dpi}）。")
        paper = self.paper if self.paper in PAPER_SIZES_MM else DEFAULT_PAPER
        out = Path(self.output_dir) if self.output_dir else None
        return ConvertOptions(
            mode=ConvertMode(self.mode),
            dpi=dpi,
            page_mode=PageMode(self.page_mode),
            paper=paper,
            orientation=Orientation(self.orientation),
            output_dir=out,
        )


# --- アプリのデータ保存先 ----------------------------------------------------
def app_data_dir() -> Path:
    """アプリのデータ保存先。

    Windows: %LOCALAPPDATA%\\ImageToPDF（未設定なら %USERPROFILE%\\AppData\\Local 配下）。
    その他 : ~/.local/share/ImageToPDF。
    """
    base = os.environ.get("LOCALAPPDATA") or None  # 空文字も未設定扱い。
    if base:
        root = Path(base)
    elif os.name == "nt":
        userprofile = os.environ.get("USERPROFILE") or None
        root = (Path(userprofile) / "AppData" / "Local") if userprofile else Path.home() / "AppData" / "Local"
    else:
        root = Path.home() / ".local" / "share"
    return root / APP_NAME


def logs_dir() -> Path:
    return app_data_dir() / "logs"


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


# --- 設定（GUI の選択状態）の保存/読込 --------------------------------------
@dataclass
class Settings:
    """GUI の最後の選択を保存しておくための永続設定。"""

    options: ConvertOptions = field(default_factory=ConvertOptions)
    last_input_dir: str | None = None

    def to_json(self) -> dict:
        d = asdict(self.options)
        # Enum / Path は JSON 化のため素の値へ。
        d["mode"] = self.options.mode.value
        d["page_mode"] = self.options.page_mode.value
        d["orientation"] = self.options.orientation.value
        d["output_dir"] = str(self.options.output_dir) if self.options.output_dir else None
        return {"options": d, "last_input_dir": self.last_input_dir}

    @staticmethod
    def from_json(data: dict) -> "Settings":
        o = data.get("options", {})
        opts = ConvertOptions(
            mode=ConvertMode(o.get("mode", ConvertMode.SINGLE.value)),
            dpi=int(o.get("dpi", DEFAULT_DPI)),
            page_mode=PageMode(o.get("page_mode", PageMode.ORIGINAL.value)),
            paper=o.get("paper", DEFAULT_PAPER),
            orientation=Orientation(o.get("orientation", Orientation.PORTRAIT.value)),
            output_dir=Path(o["output_dir"]) if o.get("output_dir") else None,
        )
        return Settings(options=opts, last_input_dir=data.get("last_input_dir"))


def load_settings() -> Settings:
    """設定を読み込む。失敗時は既定値。"""
    p = settings_path()
    try:
        if p.is_file():
            with p.open("r", encoding="utf-8") as f:
                return Settings.from_json(json.load(f))
    except Exception:
        pass
    return Settings()


def save_settings(settings: Settings) -> None:
    """設定を保存する（失敗しても例外を投げない）。"""
    try:
        app_data_dir().mkdir(parents=True, exist_ok=True)
        with settings_path().open("w", encoding="utf-8") as f:
            json.dump(settings.to_json(), f, ensure_ascii=False, indent=2)
    except Exception:
        pass
