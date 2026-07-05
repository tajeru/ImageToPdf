from pathlib import Path

from imagetopdf.config import ConvertMode, ConvertOptions
from imagetopdf.core import converter
from imagetopdf.core.converter import convert, unique_output_path


def test_unique_output_path_numbering(tmp_path):
    p1 = unique_output_path(tmp_path, "x")
    assert p1.name == "x.pdf"
    p1.write_bytes(b"%PDF-1.4")
    p2 = unique_output_path(tmp_path, "x")
    assert p2.name == "x_1.pdf"
    p2.write_bytes(b"%PDF-1.4")
    p3 = unique_output_path(tmp_path, "x")
    assert p3.name == "x_2.pdf"


def test_single_mode_end_to_end(tmp_path, make_image):
    folder = tmp_path / "doc"
    folder.mkdir()
    make_image(folder / "1.png")
    make_image(folder / "2.webp", fmt="WEBP")

    result = convert(folder, ConvertOptions(mode=ConvertMode.SINGLE))
    assert result.success_count == 1
    pdf = result.pdfs[0]
    # 入力フォルダと同じ階層（親）に出力される。
    assert pdf.parent == tmp_path
    assert pdf.name == "doc.pdf"
    assert pdf.exists()


def test_subfolders_mode_counts(tmp_path, make_image):
    root = tmp_path / "root"
    (root / "ch1").mkdir(parents=True)
    make_image(root / "ch1" / "1.png")
    (root / "ch2").mkdir()
    make_image(root / "ch2" / "1.png")

    result = convert(root, ConvertOptions(mode=ConvertMode.SUBFOLDERS))
    assert result.success_count == 2
    names = sorted(p.name for p in result.pdfs)
    assert names == ["ch1.pdf", "ch2.pdf"]


def test_failed_image_is_skipped_but_job_succeeds(tmp_path, make_image):
    folder = tmp_path / "doc"
    folder.mkdir()
    make_image(folder / "1.png")
    (folder / "2.png").write_bytes(b"broken")

    result = convert(folder, ConvertOptions(mode=ConvertMode.SINGLE))
    assert result.success_count == 1
    assert result.failed_image_count == 1


def test_cancellation_stops(tmp_path, make_image):
    folder = tmp_path / "doc"
    folder.mkdir()
    for i in range(5):
        make_image(folder / f"{i}.png")

    result = convert(
        folder,
        ConvertOptions(mode=ConvertMode.SINGLE),
        should_cancel=lambda: True,  # 即キャンセル
    )
    assert result.cancelled is True
    assert result.success_count == 0


def test_no_images_returns_empty(tmp_path):
    (tmp_path / "empty").mkdir()
    result = convert(tmp_path / "empty", ConvertOptions(mode=ConvertMode.SINGLE))
    assert result.results == []
    assert result.success_count == 0
