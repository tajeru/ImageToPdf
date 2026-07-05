from pathlib import Path

from imagetopdf.config import ConvertMode
from imagetopdf.core import scanner


def test_single_mode_collects_direct_images(tmp_path, make_image):
    make_image(tmp_path / "b.png")
    make_image(tmp_path / "a.png")
    (tmp_path / "note.txt").write_text("x")  # 対象外は無視

    jobs = scanner.find_jobs(tmp_path, ConvertMode.SINGLE)
    assert len(jobs) == 1
    job = jobs[0]
    assert [p.name for p in job.images] == ["a.png", "b.png"]
    assert job.output_name == tmp_path.name


def test_natural_sort_orders_unpadded_numbers(tmp_path, make_image):
    # ゼロ埋めしていない連番でも 1,2,...,10,11 の順に並ぶ。
    for n in [1, 2, 3, 10, 11, 21]:
        make_image(tmp_path / f"{n}.png")
    jobs = scanner.find_jobs(tmp_path, ConvertMode.SINGLE)
    names = [p.name for p in jobs[0].images]
    assert names == ["1.png", "2.png", "3.png", "10.png", "11.png", "21.png"]


def test_single_mode_empty_returns_no_jobs(tmp_path):
    (tmp_path / "sub").mkdir()
    assert scanner.find_jobs(tmp_path, ConvertMode.SINGLE) == []


def test_subfolders_only_image_only_leaf(tmp_path, make_image):
    # root には直下画像とサブフォルダが混在 → 直下画像は無視される。
    make_image(tmp_path / "loose.png")
    ch1 = tmp_path / "章1"
    ch1.mkdir()
    make_image(ch1 / "1.png")
    make_image(ch1 / "2.png")

    ch2 = tmp_path / "章2"
    ch2.mkdir()
    (ch2 / "前半").mkdir()
    make_image(ch2 / "前半" / "01.webp")
    (ch2 / "後半").mkdir()
    make_image(ch2 / "後半" / "01.png")
    # ch2 直下にも画像があるが、ch2 はサブフォルダを持つので無視される。
    make_image(ch2 / "ignored.png")

    jobs = scanner.find_jobs(tmp_path, ConvertMode.SUBFOLDERS)
    names = sorted(j.output_name for j in jobs)
    assert names == ["前半", "後半", "章1"]
    # loose.png（root 直下）と ignored.png（ch2 直下）は含まれない。
    all_imgs = {p.name for j in jobs for p in j.images}
    assert "loose.png" not in all_imgs
    assert "ignored.png" not in all_imgs


def test_subfolders_root_is_leaf(tmp_path, make_image):
    # root 自体が画像のみ（サブフォルダ無し）なら root を1ジョブにする。
    make_image(tmp_path / "a.png")
    jobs = scanner.find_jobs(tmp_path, ConvertMode.SUBFOLDERS)
    assert len(jobs) == 1
    assert jobs[0].folder == tmp_path


def test_subfolders_empty_subdir_does_not_drop_loose_images(tmp_path, make_image):
    # 画像を含むフォルダに「空のサブフォルダ」があっても直下画像は捨てない。
    folder = tmp_path / "chapter"
    folder.mkdir()
    make_image(folder / "1.png")
    make_image(folder / "2.png")
    (folder / "extras").mkdir()  # 空（画像なし）

    jobs = scanner.find_jobs(tmp_path, ConvertMode.SUBFOLDERS)
    assert len(jobs) == 1
    assert jobs[0].folder == folder
    assert [p.name for p in jobs[0].images] == ["1.png", "2.png"]


def test_subfolders_image_subdir_makes_parent_ignore_loose(tmp_path, make_image):
    # 画像を含むサブフォルダがある場合は“親”扱いで直下画像は無視。
    folder = tmp_path / "book"
    folder.mkdir()
    make_image(folder / "cover.png")  # 直下画像（無視される）
    (folder / "ch1").mkdir()
    make_image(folder / "ch1" / "1.png")

    jobs = scanner.find_jobs(tmp_path, ConvertMode.SUBFOLDERS)
    names = sorted(j.output_name for j in jobs)
    assert names == ["ch1"]
