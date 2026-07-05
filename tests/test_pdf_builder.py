import pytest

from imagetopdf.config import ConvertOptions, Orientation, PageMode
from imagetopdf.core.pdf_builder import build_pdf

pypdf = pytest.importorskip("pypdf")


def _page_sizes(pdf_path):
    reader = pypdf.PdfReader(str(pdf_path))
    sizes = []
    for page in reader.pages:
        box = page.mediabox
        sizes.append((float(box.width), float(box.height)))
    return sizes


def test_original_mode_dpi_controls_page_size(tmp_path, make_image):
    # 300x600 px を 300dpi にすると 1in x 2in = 72pt x 144pt。
    img = make_image(tmp_path / "a.png", size=(300, 600))
    out = tmp_path / "out.pdf"
    opts = ConvertOptions(dpi=300, page_mode=PageMode.ORIGINAL)
    build_pdf([img], out, opts)

    sizes = _page_sizes(out)
    assert len(sizes) == 1
    w, h = sizes[0]
    assert w == pytest.approx(72, abs=1)
    assert h == pytest.approx(144, abs=1)


def test_fixed_a4_portrait_uniform_pages(tmp_path, make_image):
    a = make_image(tmp_path / "a.png", size=(300, 600))
    b = make_image(tmp_path / "b.png", size=(800, 400))  # 別アスペクト比
    out = tmp_path / "out.pdf"
    opts = ConvertOptions(
        page_mode=PageMode.FIXED, paper="A4", orientation=Orientation.PORTRAIT
    )
    build_pdf([a, b], out, opts)

    sizes = _page_sizes(out)
    assert len(sizes) == 2
    # 全ページが A4 縦（595.27 x 841.89 pt）に統一されている。
    for w, h in sizes:
        assert w == pytest.approx(595.27, abs=1.5)
        assert h == pytest.approx(841.89, abs=1.5)


def test_multiple_images_make_multiple_pages(tmp_path, make_image):
    imgs = [make_image(tmp_path / f"{i}.png") for i in range(3)]
    out = tmp_path / "out.pdf"
    build_pdf(imgs, out, ConvertOptions())
    assert len(_page_sizes(out)) == 3
