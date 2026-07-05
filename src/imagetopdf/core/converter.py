"""変換ジョブのオーケストレーション。

scanner → decoder → pdf_builder を束ね、進捗通知とキャンセルに対応する。
GUI 非依存（CLI や単体テストからも呼べる）。
"""
from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..config import ConvertMode, ConvertOptions
from ..logging_setup import get_logger
from .decoder import DecodeError, prepare_image
from .pdf_builder import PdfBuildError, build_pdf
from .scanner import ConvertJob, find_jobs

log = get_logger(__name__)

# 進捗コールバック: (done_images, total_images, current_path|None)
ProgressCb = Callable[[int, int, "Path | None"], None]
# 状態メッセージコールバック: (message)
StatusCb = Callable[[str], None]
# キャンセル判定: () -> bool
CancelCb = Callable[[], bool]


@dataclass
class JobResult:
    job: ConvertJob
    pdf_path: Path | None = None
    failed_images: list[tuple[Path, str]] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.pdf_path is not None


@dataclass
class ConvertResult:
    results: list[JobResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def pdfs(self) -> list[Path]:
        return [r.pdf_path for r in self.results if r.pdf_path]

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def failed_image_count(self) -> int:
        return sum(len(r.failed_images) for r in self.results)

    @property
    def job_error_count(self) -> int:
        return sum(1 for r in self.results if r.error)


def unique_output_path(directory: Path, base_name: str) -> Path:
    """既存ファイルがあれば _1, _2 … と連番を付けて衝突を避ける（§5.5）。"""
    candidate = directory / f"{base_name}.pdf"
    if not candidate.exists():
        return candidate
    i = 1
    while True:
        candidate = directory / f"{base_name}_{i}.pdf"
        if not candidate.exists():
            return candidate
        i += 1


def _output_dir_for(job: ConvertJob, options: ConvertOptions) -> Path:
    """出力先ディレクトリ。未指定なら入力フォルダと同じ階層（＝親）。"""
    if options.output_dir is not None:
        return Path(options.output_dir)
    return job.folder.parent


def _noop(*_args, **_kwargs) -> None:  # pragma: no cover - 既定コールバック
    return None


def convert(
    root: Path,
    options: ConvertOptions,
    on_progress: ProgressCb | None = None,
    on_status: StatusCb | None = None,
    should_cancel: CancelCb | None = None,
) -> ConvertResult:
    """root を options に従って変換する。"""
    options = options.validated()
    on_progress = on_progress or _noop
    on_status = on_status or _noop
    should_cancel = should_cancel or (lambda: False)

    jobs = find_jobs(Path(root), options.mode)
    result = ConvertResult()

    if not jobs:
        on_status("対象となる画像が見つかりませんでした。")
        return result

    total_images = sum(j.image_count for j in jobs)
    done = 0
    on_progress(done, total_images, None)

    for job in jobs:
        if should_cancel():
            result.cancelled = True
            break

        mode_label = "フォルダ" if options.mode == ConvertMode.SINGLE else "サブフォルダ"
        on_status(f"{mode_label}「{job.folder.name}」を変換中… ({job.image_count}枚)")

        jr = JobResult(job=job)
        tmp = Path(tempfile.mkdtemp(prefix="imagetopdf_"))
        prepared: list[Path] = []
        try:
            for idx, src in enumerate(job.images):
                if should_cancel():
                    result.cancelled = True
                    break
                on_progress(done, total_images, src)
                try:
                    prepared.append(prepare_image(src, tmp, idx))
                except DecodeError as e:
                    jr.failed_images.append((src, str(e)))
                    log.warning("画像をスキップ: %s", e)
                done += 1
                on_progress(done, total_images, src)

            if result.cancelled:
                break

            if not prepared:
                jr.error = "対象画像をすべてスキップしたため PDF を作成しませんでした。"
                log.warning("%s: %s", job.folder, jr.error)
            else:
                out_dir = _output_dir_for(job, options)
                out_path = unique_output_path(out_dir, job.output_name)
                try:
                    jr.pdf_path = build_pdf(prepared, out_path, options)
                    log.info("PDF生成: %s (%d枚)", jr.pdf_path, len(prepared))
                except PdfBuildError as e:
                    jr.error = str(e)
                    log.error("%s: %s", job.folder, e)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        result.results.append(jr)

    on_progress(done, total_images, None)
    return result
