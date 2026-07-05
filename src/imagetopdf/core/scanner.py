"""フォルダ走査・変換ジョブの列挙。

モードA（SINGLE）  : 選択フォルダ直下の画像を1ジョブにする。
モードB（SUBFOLDERS）: 「中身が画像のみ（サブフォルダを含まない）」フォルダだけを
                       1ジョブにする。サブフォルダを持つフォルダの直下画像は無視し、
                       サブフォルダ側を再帰的に走査する（技術指示書 §5.2）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import SUPPORTED_EXTS, ConvertMode
from ..logging_setup import get_logger

log = get_logger(__name__)

_NUM_RE = re.compile(r"\d+|\D+")


def natural_key(name: str) -> list:
    """自然順ソート用キー。

    数字部分を数値として比較するため、`1, 2, 10` が正しく並ぶ。
    ゼロ埋め（`01, 02`）でも通常の連番（`1, 2, 10`）でも意図どおりになる。
    """
    parts = _NUM_RE.findall(name)
    # (is_text, value) のタプル列にして型混在の比較エラーを避ける。
    return [(False, int(t)) if t.isdigit() else (True, t.lower()) for t in parts]


def is_image_file(path: Path) -> bool:
    """対応拡張子の画像ファイルか（大小文字を区別しない）。"""
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTS


def list_images(folder: Path) -> list[Path]:
    """folder 直下（非再帰）の対象画像を自然順（名前順）で返す。"""
    imgs = [p for p in folder.iterdir() if is_image_file(p)]
    imgs.sort(key=lambda p: natural_key(p.name))
    return imgs


def _has_subdirs(folder: Path) -> bool:
    return any(p.is_dir() for p in folder.iterdir())


@dataclass
class ConvertJob:
    """1つの出力 PDF に対応する変換ジョブ。"""

    folder: Path           # 画像が入っているフォルダ
    images: list[Path] = field(default_factory=list)  # 名前順の画像
    output_name: str = ""  # 出力 PDF のベース名（拡張子なし）

    @property
    def image_count(self) -> int:
        return len(self.images)


def _collect_leaf_jobs(folder: Path, jobs: list[ConvertJob]) -> None:
    """SUBFOLDERS 用の再帰収集。

    「画像を含むサブフォルダ」を持つフォルダは“親”とみなし、直下画像は無視して
    各サブフォルダへ再帰する（§5.2）。逆に、サブフォルダが空／画像を持たない場合は
    このフォルダを“末端”とみなし、直下画像があればジョブ化する。
    （空の 'thumbs' 等のサブフォルダがあるだけで直下画像が捨てられる事故を防ぐ。）

    直下画像を無視する場合は、見落としを防ぐため警告ログを出す。
    """
    try:
        children = list(folder.iterdir())
    except (PermissionError, OSError):
        return

    subdirs = sorted((p for p in children if p.is_dir()), key=lambda p: natural_key(p.name))

    before = len(jobs)
    for sub in subdirs:
        _collect_leaf_jobs(sub, jobs)
    subdirs_produced = len(jobs) > before

    images = list_images(folder)
    if not images:
        return

    if subdirs_produced:
        # 画像を含むサブフォルダがある → このフォルダは“親”。直下画像は無視。
        log.warning(
            "フォルダ「%s」の直下画像 %d 枚は、画像を含むサブフォルダがあるため無視しました。",
            folder.name,
            len(images),
        )
    else:
        # 画像を含むサブフォルダが無い → このフォルダを末端としてジョブ化。
        jobs.append(ConvertJob(folder=folder, images=images, output_name=folder.name))


def find_jobs(root: Path, mode: ConvertMode) -> list[ConvertJob]:
    """変換対象ジョブの一覧を返す。"""
    root = Path(root)
    if not root.is_dir():
        return []

    if mode == ConvertMode.SINGLE:
        images = list_images(root)
        if not images:
            return []
        return [ConvertJob(folder=root, images=images, output_name=root.name)]

    # SUBFOLDERS
    jobs: list[ConvertJob] = []
    _collect_leaf_jobs(root, jobs)
    return jobs
