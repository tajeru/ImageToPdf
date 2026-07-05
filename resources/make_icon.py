"""resources/app.ico を生成するスクリプト。

使い方:  python resources/make_icon.py
依存:     Pillow
画像（写真）→ PDF を表す簡単なアイコンを描いて .ico に保存する。
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 256
OUT = Path(__file__).with_name("app.ico")

BG = (37, 99, 235)        # 青
PAGE = (255, 255, 255)
PAGE_EDGE = (203, 213, 225)
SKY = (191, 219, 254)
HILL = (34, 197, 94)      # 緑
SUN = (250, 204, 21)      # 黄
PDF_RED = (220, 38, 38)


def _font(size: int):
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_icon() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 角丸の青背景。
    d.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=44, fill=BG)

    # 白いページ（右上に折り返し）。
    px0, py0, px1, py1 = 56, 40, 200, 216
    fold = 34
    d.polygon(
        [(px0, py0), (px1 - fold, py0), (px1, py0 + fold), (px1, py1), (px0, py1)],
        fill=PAGE,
        outline=PAGE_EDGE,
    )
    d.polygon([(px1 - fold, py0), (px1, py0 + fold), (px1 - fold, py0 + fold)], fill=PAGE_EDGE)

    # ページ上部に画像（空・太陽・山）のサムネ。
    iw0, iw1 = px0 + 16, px1 - 16
    ih0, ih1 = py0 + 22, py0 + 92
    d.rectangle([iw0, ih0, iw1, ih1], fill=SKY)
    d.ellipse([iw1 - 34, ih0 + 6, iw1 - 12, ih0 + 28], fill=SUN)
    d.polygon([(iw0, ih1), (iw0 + 38, ih1 - 40), (iw0 + 70, ih1)], fill=HILL)
    d.polygon([(iw0 + 50, ih1), (iw0 + 86, ih1 - 30), (iw1, ih1)], fill=(22, 163, 74))

    # 下部に PDF ラベル。
    d.rounded_rectangle([px0 + 8, py1 - 56, px1 - 8, py1 - 12], radius=10, fill=PDF_RED)
    f = _font(34)
    text = "PDF"
    tb = d.textbbox((0, 0), text, font=f)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    d.text(
        ((px0 + px1) / 2 - tw / 2 - tb[0], (py1 - 34) - th / 2 - tb[1]),
        text,
        font=f,
        fill=(255, 255, 255),
    )
    return img


def main() -> None:
    base = draw_icon()
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base.save(OUT, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
