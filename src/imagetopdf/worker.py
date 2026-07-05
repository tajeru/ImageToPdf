"""変換処理を別スレッドで走らせる QThread ワーカー。

UI スレッドをブロックしないよう、core/converter を別スレッドで実行し、
進捗・状態・完了・致命的エラーをシグナルで GUI に通知する。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .config import ConvertOptions
from .core.converter import ConvertResult, convert
from .core.update import (
    AssetInfo,
    UpdateCheckError,
    UpdateDownloadCancelled,
    UpdateDownloadError,
    download_asset,
    fetch_latest_release,
)
from .logging_setup import get_logger

log = get_logger(__name__)


class ConvertWorker(QThread):
    # done, total, current_name（無ければ ""）
    progress = Signal(int, int, str)
    # 状態メッセージ
    status = Signal(str)
    # 正常終了（ConvertResult を載せる）
    completed = Signal(object)
    # 致命的エラー（想定外例外）
    failed = Signal(str)

    def __init__(self, root: Path, options: ConvertOptions, parent=None) -> None:
        super().__init__(parent)
        self._root = Path(root)
        self._options = options
        self._cancel = False

    def cancel(self) -> None:
        """協調的キャンセルを要求する。"""
        self._cancel = True

    # QThread のエントリポイント（別スレッドで実行される）。
    def run(self) -> None:  # noqa: D401
        def on_progress(done: int, total: int, current) -> None:
            name = Path(current).name if current else ""
            self.progress.emit(done, total, name)

        def on_status(msg: str) -> None:
            self.status.emit(msg)

        def should_cancel() -> bool:
            return self._cancel

        try:
            result: ConvertResult = convert(
                self._root,
                self._options,
                on_progress=on_progress,
                on_status=on_status,
                should_cancel=should_cancel,
            )
            self.completed.emit(result)
        except Exception as e:  # noqa: BLE001 - 想定外は致命扱いで通知
            log.exception("変換中に致命的エラー")
            self.failed.emit(str(e))


class UpdateCheckWorker(QThread):
    """GitHub の最新リリースを問い合わせる（別スレッド・ネットワークI/O）。"""

    # 公開リリースが見つかった場合は ReleaseInfo、無ければ None を emit。
    checked = Signal(object)
    failed = Signal(str)

    def run(self) -> None:  # noqa: D401
        try:
            release = fetch_latest_release()
            self.checked.emit(release)
        except UpdateCheckError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001
            log.exception("アップデート確認に失敗")
            self.failed.emit(str(e))


class UpdateDownloadWorker(QThread):
    """アップデートアセットを別スレッドでダウンロードする。"""

    progress = Signal(int, int)  # done_bytes, total_bytes
    completed = Signal(object)  # 保存先 Path
    cancelled = Signal()
    failed = Signal(str)

    def __init__(self, asset: AssetInfo, dest_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self._asset = asset
        self._dest_dir = Path(dest_dir)
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:  # noqa: D401
        try:
            path = download_asset(
                self._asset,
                self._dest_dir,
                on_progress=lambda done, total: self.progress.emit(done, total),
                should_cancel=lambda: self._cancel,
            )
            self.completed.emit(path)
        except UpdateDownloadCancelled:
            self.cancelled.emit()
        except UpdateDownloadError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001
            log.exception("アップデートのダウンロードに失敗")
            self.failed.emit(str(e))
