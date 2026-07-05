"""img2pdf を使った PDF 生成。DPI / ページサイズを適用する。"""
from __future__ import annotations

from pathlib import Path

import img2pdf

from ..config import (
    PAPER_SIZES_MM,
    ConvertOptions,
    Orientation,
    PageMode,
)
from ..logging_setup import get_logger

log = get_logger(__name__)


class PdfBuildError(Exception):
    """PDF 生成に失敗。"""


def _layout_fun(options: ConvertOptions):
    """ConvertOptions から img2pdf の layout 関数を作る。"""
    if options.page_mode == PageMode.ORIGINAL:
        # 画像そのまま：指定 DPI で「画素数 ÷ DPI＝物理サイズ」。
        return img2pdf.get_fixed_dpi_layout_fun((options.dpi, options.dpi))

    # FIXED：用紙サイズに統一し、画像はアスペクト比保持で内側にフィット。
    w_mm, h_mm = PAPER_SIZES_MM.get(options.paper, PAPER_SIZES_MM["A4"])
    if options.orientation == Orientation.LANDSCAPE:
        w_mm, h_mm = h_mm, w_mm
    pagesize = (img2pdf.mm_to_pt(w_mm), img2pdf.mm_to_pt(h_mm))
    auto = options.orientation == Orientation.AUTO
    return img2pdf.get_layout_fun(pagesize=pagesize, auto_orient=auto)


def build_pdf(image_paths: list[Path], output_path: Path, options: ConvertOptions) -> Path:
    """画像列を1つの PDF にまとめて output_path に書き出す。

    Returns:
        実際に書き出した PDF のパス。

    Raises:
        PdfBuildError: 画像が空、または img2pdf が失敗した場合。
    """
    if not image_paths:
        raise PdfBuildError("画像が1枚もありません。")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    layout = _layout_fun(options)
    srcs = [str(p) for p in image_paths]

    try:
        with output_path.open("wb") as f:
            img2pdf.convert(*srcs, outputstream=f, layout_fun=layout)
    except Exception as e:  # noqa: BLE001 - img2pdf は多様な例外を投げる
        # 中途半端な PDF を残さない。
        try:
            if output_path.exists():
                output_path.unlink()
        except OSError:
            pass
        raise PdfBuildError(f"PDF 生成に失敗しました: {e}") from e

    return output_path
