"""画像のデコードと img2pdf 向けの正規化。

方針（技術指示書 §5.3）:
  - PNG / JPEG で「アルファ無し・素直なモード」なら **無変換でそのまま** img2pdf に渡す
    （img2pdf は JPEG/PNG を再エンコードせず埋め込むため、品質劣化もファイル肥大も無い）。
  - WEBP は常に Pillow でデコード → 一時 PNG（可逆）に変換。
  - アルファを含む画像は白背景で合成（PDF/img2pdf は透過非対応）。
  - CMYK / パレット / 16bit など img2pdf が嫌う形式は RGB 化して一時 PNG に正規化。
  - アニメーション WEBP は先頭フレームのみ使用（seek しない）。
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from ..logging_setup import get_logger

log = get_logger(__name__)

# Pillow の「decompression bomb」上限を緩める（巨大スキャン画像対策）。
# None にすると警告/例外を出さない。安全性より実用を優先。
Image.MAX_IMAGE_PIXELS = None

# img2pdf にそのまま渡してよい「素直な」モード。
_SAFE_MODES = {"RGB", "L", "1"}
# 無変換パススルーを許す拡張子。
_PASSTHROUGH_EXTS = {".png", ".jpg", ".jpeg"}


class DecodeError(Exception):
    """1枚の画像のデコード/正規化に失敗。"""


def _has_alpha(img: Image.Image) -> bool:
    if img.mode in ("RGBA", "LA", "PA"):
        return True
    if img.mode == "P" and "transparency" in img.info:
        return True
    return "transparency" in img.info


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    """アルファを白背景で合成し、RGB 画像を返す。"""
    if img.mode == "P":
        img = img.convert("RGBA")
    if img.mode in ("RGBA", "LA", "PA"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return img.convert("RGB")


def _normalize_to_rgb(img: Image.Image) -> Image.Image:
    """どんなモードでも安全に RGB へ。EXIF の向きも適用する。"""
    # EXIF Orientation を反映（スマホ撮影 JPEG 等）。
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    if _has_alpha(img):
        return _flatten_to_rgb(img)

    if img.mode in ("RGB", "L"):
        return img.convert("RGB")

    # 16bit/32bit/float グレースケール → 線形スケールで 8bit へ（階調を忠実に）。
    if img.mode in ("I", "I;16", "I;16B", "I;16L"):
        # 16bit 値(0-65535)を 8bit(0-255)へ線形縮小。autocontrast は使わない
        # （ページごとに勝手にレベル補正され、見た目が変わってしまうため）。
        # ※ mode "I" の point は式オブジェクトを受けるので乗算で表現する。
        img = img.convert("I").point(lambda v: v * (1.0 / 256)).convert("L")
        return img.convert("RGB")
    if img.mode == "F":
        # 浮動小数グレースケールは min-max で 0-255 に線形正規化。
        lo, hi = img.getextrema()
        span = (hi - lo) or 1.0
        img = img.point(lambda v: (v - lo) * (255.0 / span)).convert("L")
        return img.convert("RGB")

    # CMYK / パレット / YCbCr など。
    return img.convert("RGB")


def prepare_image(src: Path, temp_dir: Path, index: int) -> Path:
    """1枚を img2pdf に渡せるパスへ変換して返す。

    無変換で渡せる場合は src をそのまま返し、正規化が必要な場合のみ
    temp_dir に連番 PNG を書き出してそのパスを返す。

    Raises:
        DecodeError: 画像が壊れている等でデコードできない。
    """
    src = Path(src)
    ext = src.suffix.lower()
    try:
        with Image.open(src) as img:
            img.load()  # 破損検知のため明示ロード。
            needs_norm = (
                ext not in _PASSTHROUGH_EXTS
                or img.mode not in _SAFE_MODES
                or _has_alpha(img)
                or getattr(img, "is_animated", False)
            )
            if not needs_norm:
                # PNG/JPEG かつ素直 → 無変換パススルー（高品質・高速）。
                return src

            rgb = _normalize_to_rgb(img)
    except DecodeError:
        raise
    except Exception as e:  # noqa: BLE001 - Pillow は多様な例外を投げる
        raise DecodeError(f"{src.name}: デコード失敗: {e}") from e

    out = temp_dir / f"{index:06d}.png"
    try:
        # PNG（可逆）で保存。img2pdf 側で埋め込まれる。
        rgb.save(out, format="PNG")
    except Exception as e:  # noqa: BLE001
        raise DecodeError(f"{src.name}: 一時PNGの書き出し失敗: {e}") from e
    return out
