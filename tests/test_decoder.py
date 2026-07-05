import pytest
from PIL import Image

from imagetopdf.core.decoder import DecodeError, prepare_image


def test_plain_png_passthrough(tmp_path, make_image):
    src = make_image(tmp_path / "p.png")
    out = prepare_image(src, tmp_path, 0)
    assert out == src  # 無変換パススルー


def test_plain_jpeg_passthrough(tmp_path, make_image):
    src = make_image(tmp_path / "p.jpg", fmt="JPEG")
    out = prepare_image(src, tmp_path, 0)
    assert out == src


def test_webp_is_normalized(tmp_path, make_image):
    src = make_image(tmp_path / "p.webp", fmt="WEBP")
    out = prepare_image(src, tmp_path, 3)
    assert out != src
    assert out.suffix == ".png"
    assert out.name == "000003.png"
    with Image.open(out) as im:
        assert im.mode == "RGB"


def test_rgba_png_flattened_to_rgb(tmp_path):
    src = tmp_path / "alpha.png"
    Image.new("RGBA", (50, 50), (255, 0, 0, 128)).save(src)
    out = prepare_image(src, tmp_path, 1)
    assert out != src  # アルファ有りは正規化される
    with Image.open(out) as im:
        assert im.mode == "RGB"


def test_16bit_grayscale_faithful_downscale(tmp_path):
    # 16bit グレースケールは線形に 8bit 化される（autocontrast でレベルが
    # 変わらない）。値 30000 (>>8 = 117) が概ね保たれることを確認。
    src = tmp_path / "scan.png"
    Image.new("I;16", (20, 20), 30000).save(src)
    out = prepare_image(src, tmp_path, 0)
    with Image.open(out) as im:
        assert im.mode == "RGB"
        r, g, b = im.getpixel((10, 10))
        assert abs(r - (30000 >> 8)) <= 2


def test_broken_file_raises(tmp_path):
    bad = tmp_path / "broken.png"
    bad.write_bytes(b"not really a png")
    with pytest.raises(DecodeError):
        prepare_image(bad, tmp_path, 0)
