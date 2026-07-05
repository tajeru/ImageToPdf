"""メインウィンドウ。

画面は「ヘッダー → 入力（ドロップ領域） → 変換設定カード → 進捗 → アクション」
の縦積みで構成し、各セクションを _build_* メソッドに分割している。
文言は ui/strings.py、配色・スタイルは ui/theme.py に集約。
変換ロジックは持たず、worker 経由で core を呼ぶだけ（技術指示書 §4.1）。
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__
from ..config import (
    DEFAULT_DPI,
    MAX_DPI,
    MIN_DPI,
    PAPER_SIZES_MM,
    ConvertMode,
    ConvertOptions,
    Orientation,
    PageMode,
    Settings,
    load_settings,
    save_settings,
)
from ..core import update
from ..core.converter import ConvertResult
from ..core.update import AssetInfo, ReleaseInfo
from ..worker import ConvertWorker, UpdateCheckWorker, UpdateDownloadWorker
from . import strings, theme
from .widgets import (
    ComboBox,
    ElidedLabel,
    FolderDropArea,
    SegmentedControl,
    SpinBox,
    logo_pixmap,
)


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("window")
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.setMinimumWidth(680)

        self._input_dir: Path | None = None
        self._output_dir: Path | None = None
        self._worker: ConvertWorker | None = None
        self._last_open_dir: Path | None = None
        self._update_check_worker: UpdateCheckWorker | None = None
        self._update_download_worker: UpdateDownloadWorker | None = None

        self._build_ui()
        self._restore_settings()
        theme.enable_dark_title_bar(self)
        self.resize(720, max(700, self.sizeHint().height()))

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(16)

        root.addLayout(self._build_header())

        self.drop = FolderDropArea()
        self.drop.folderDropped.connect(self._on_folder_chosen)
        self.drop.clicked.connect(self._pick_input)
        root.addWidget(self.drop, 1)

        root.addWidget(self._build_options_card())
        root.addLayout(self._build_progress_section())
        root.addLayout(self._build_actions())

        # 変換中に無効化する入力群（キャンセル以外）。
        self._lockable: tuple[QWidget, ...] = (
            self.drop,
            self.seg_mode,
            self.spin_dpi,
            self.seg_page,
            self.cmb_paper,
            self.cmb_orient,
            self.seg_out,
            self.btn_out,
            self.btn_start,
            self.btn_update,
        )

        self._update_mode_hint()
        self._update_page_controls()
        self._update_output_controls()

    def _build_header(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(14)

        logo = QLabel()
        logo.setPixmap(logo_pixmap(44, self.devicePixelRatioF()))
        lay.addWidget(logo, 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(2)
        name_row = QHBoxLayout()
        name_row.setSpacing(10)
        title = QLabel(APP_NAME)
        title.setProperty("cls", "h1")
        chip = QLabel(f"v{__version__}")
        chip.setProperty("cls", "chip")
        name_row.addWidget(title)
        name_row.addWidget(chip, 0, Qt.AlignVCenter)
        name_row.addStretch(1)
        self.btn_update = QPushButton(strings.BTN_UPDATE)
        self.btn_update.setProperty("cls", "ghostSmall")
        self.btn_update.setCursor(Qt.PointingHandCursor)
        self.btn_update.clicked.connect(self._check_for_update)
        name_row.addWidget(self.btn_update, 0, Qt.AlignVCenter)
        col.addLayout(name_row)

        tagline = QLabel(strings.TAGLINE)
        tagline.setProperty("cls", "tagline")
        col.addWidget(tagline)
        lay.addLayout(col, 1)
        return lay

    def _build_options_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("cls", "card")
        grid = QGridLayout(card)
        grid.setContentsMargins(22, 18, 22, 18)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.setColumnMinimumWidth(0, 78)
        grid.setColumnStretch(1, 1)

        # 変換モード
        self.seg_mode = SegmentedControl()
        self.seg_mode.addSegment(strings.MODE_SINGLE, ConvertMode.SINGLE)
        self.seg_mode.addSegment(strings.MODE_SUBFOLDERS, ConvertMode.SUBFOLDERS)
        self.lbl_mode_hint = QLabel()
        self.lbl_mode_hint.setProperty("cls", "hint")
        self.seg_mode.dataChanged.connect(self._update_mode_hint)
        grid.addWidget(self._field_label(strings.FIELD_MODE), 0, 0)
        grid.addLayout(self._hrow(self.seg_mode), 0, 1)
        grid.addWidget(self.lbl_mode_hint, 1, 1)

        # 解像度
        self.spin_dpi = SpinBox()
        self.spin_dpi.setRange(MIN_DPI, MAX_DPI)
        self.spin_dpi.setValue(DEFAULT_DPI)
        self.spin_dpi.setSuffix(" dpi")
        self.spin_dpi.setFixedWidth(112)
        dpi_hint = QLabel(strings.DPI_HINT)
        dpi_hint.setProperty("cls", "hint")
        grid.addWidget(self._field_label(strings.FIELD_DPI), 2, 0)
        grid.addLayout(self._hrow(self.spin_dpi, dpi_hint), 2, 1)

        # ページサイズ
        self.seg_page = SegmentedControl()
        self.seg_page.addSegment(strings.PAGE_ORIGINAL, PageMode.ORIGINAL)
        self.seg_page.addSegment(strings.PAGE_FIXED, PageMode.FIXED)
        self.cmb_paper = ComboBox()
        self.cmb_paper.addItems(list(PAPER_SIZES_MM.keys()))
        self.cmb_orient = ComboBox()
        self.cmb_orient.addItem(strings.ORIENT_PORTRAIT, Orientation.PORTRAIT.value)
        self.cmb_orient.addItem(strings.ORIENT_LANDSCAPE, Orientation.LANDSCAPE.value)
        self.cmb_orient.addItem(strings.ORIENT_AUTO, Orientation.AUTO.value)
        self.seg_page.dataChanged.connect(self._update_page_controls)
        grid.addWidget(self._field_label(strings.FIELD_PAGE), 3, 0)
        grid.addLayout(self._hrow(self.seg_page, self.cmb_paper, self.cmb_orient), 3, 1)

        # 出力先
        self.seg_out = SegmentedControl()
        self.seg_out.addSegment(strings.OUT_SAME, False)
        self.seg_out.addSegment(strings.OUT_CUSTOM, True)
        self.btn_out = QPushButton(strings.BTN_PICK_OUT)
        self.btn_out.setProperty("cls", "ghostSmall")
        self.btn_out.setCursor(Qt.PointingHandCursor)
        self.btn_out.clicked.connect(self._pick_output)
        self.lbl_out = ElidedLabel()
        self.lbl_out.setProperty("cls", "hint")
        self.seg_out.dataChanged.connect(self._update_output_controls)
        grid.addWidget(self._field_label(strings.FIELD_OUTPUT), 4, 0)
        grid.addLayout(self._hrow(self.seg_out, self.btn_out), 4, 1)
        grid.addWidget(self.lbl_out, 5, 1)

        return card

    def _build_progress_section(self) -> QVBoxLayout:
        lay = QVBoxLayout()
        lay.setSpacing(8)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        lay.addWidget(self.progress)
        self.lbl_status = ElidedLabel(strings.STATUS_IDLE, mode=Qt.ElideRight)
        self.lbl_status.setProperty("cls", "status")
        lay.addWidget(self.lbl_status)
        return lay

    def _build_actions(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(10)
        self.btn_open = QPushButton(strings.BTN_OPEN_OUTPUT)
        self.btn_open.setProperty("cls", "ghost")
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self._open_output)
        self.btn_open.setEnabled(False)
        lay.addWidget(self.btn_open)
        lay.addStretch(1)

        self.btn_cancel = QPushButton(strings.BTN_CANCEL)
        self.btn_cancel.setProperty("cls", "ghost")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_cancel.setEnabled(False)
        self.btn_start = QPushButton(strings.BTN_START)
        self.btn_start.setProperty("cls", "primary")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._start)
        lay.addWidget(self.btn_cancel)
        lay.addWidget(self.btn_start)
        return lay

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("cls", "field")
        return label

    @staticmethod
    def _hrow(*widgets: QWidget) -> QHBoxLayout:
        """ウィジェットを左詰めで並べる行レイアウト。"""
        row = QHBoxLayout()
        row.setSpacing(8)
        for w in widgets:
            row.addWidget(w)
        row.addStretch(1)
        return row

    # -------------------------------------------------------------- helpers
    def _set_status(self, text: str, state: str = "") -> None:
        """状態ラベルを更新する。state は "" / "ok" / "error"。"""
        self.lbl_status.setFullText(text)
        if self.lbl_status.property("state") != state:
            self.lbl_status.setProperty("state", state)
            theme.repolish(self.lbl_status)

    def _update_mode_hint(self, _data: object = None) -> None:
        single = self.seg_mode.currentData() == ConvertMode.SINGLE
        self.lbl_mode_hint.setText(
            strings.MODE_HINT_SINGLE if single else strings.MODE_HINT_SUBFOLDERS
        )

    def _update_page_controls(self, _data: object = None) -> None:
        fixed = self.seg_page.currentData() == PageMode.FIXED
        self.cmb_paper.setEnabled(fixed)
        self.cmb_orient.setEnabled(fixed)

    def _update_output_controls(self, _data: object = None) -> None:
        custom = bool(self.seg_out.currentData())
        self.btn_out.setEnabled(custom)
        self.lbl_out.setVisible(custom)

    def _on_folder_chosen(self, folder: str) -> None:
        self._input_dir = Path(folder)
        self.drop.show_selection(folder)
        self._set_status(strings.STATUS_READY)

    def _pick_input(self) -> None:
        start = str(self._input_dir) if self._input_dir else ""
        folder = QFileDialog.getExistingDirectory(self, strings.DLG_PICK_INPUT, start)
        if folder:
            self._on_folder_chosen(folder)

    def _pick_output(self) -> None:
        start = str(self._output_dir) if self._output_dir else ""
        folder = QFileDialog.getExistingDirectory(self, strings.DLG_PICK_OUTPUT, start)
        if folder:
            self._output_dir = Path(folder)
            self.lbl_out.setFullText(strings.OUT_PREFIX.format(path=folder))

    def _build_options(self) -> ConvertOptions:
        out_dir = self._output_dir if bool(self.seg_out.currentData()) else None
        return ConvertOptions(
            mode=self.seg_mode.currentData(),
            dpi=self.spin_dpi.value(),
            page_mode=self.seg_page.currentData(),
            paper=self.cmb_paper.currentText(),
            orientation=Orientation(self.cmb_orient.currentData()),
            output_dir=out_dir,
        ).validated()

    def _set_running(self, running: bool) -> None:
        for w in self._lockable:
            w.setEnabled(not running)
        self.btn_cancel.setEnabled(running)
        if not running:
            self._update_page_controls()
            self._update_output_controls()

    # ----------------------------------------------------------------- flow
    def _start(self) -> None:
        if not self._input_dir or not self._input_dir.is_dir():
            QMessageBox.warning(self, APP_NAME, strings.WARN_NO_INPUT)
            return
        if bool(self.seg_out.currentData()) and not self._output_dir:
            QMessageBox.warning(self, APP_NAME, strings.WARN_NO_OUTPUT)
            return
        try:
            options = self._build_options()
        except ValueError as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return

        self.btn_open.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self._set_running(True)
        self._set_status(strings.STATUS_STARTED)

        self._worker = ConvertWorker(self._input_dir, options)
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._set_status)
        self._worker.completed.connect(self._on_completed)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_thread_finished)
        self._worker.start()

    def _cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
            self.btn_cancel.setEnabled(False)
            self._set_status(strings.STATUS_CANCELLING)

    def _on_progress(self, done: int, total: int, current: str) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)
        if current:
            self._set_status(strings.STATUS_PROGRESS.format(done=done, total=total, name=current))

    def _on_completed(self, result: ConvertResult) -> None:
        self._set_running(False)
        self.progress.setValue(self.progress.maximum())

        # 「出力フォルダを開く」用に、最初に生成した PDF の場所を覚える。
        if result.pdfs:
            self._last_open_dir = result.pdfs[0].parent
            self.btn_open.setEnabled(True)

        self._show_summary(result)

    def _on_failed(self, message: str) -> None:
        self._set_running(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self._set_status(strings.STATUS_ERROR, state="error")
        QMessageBox.critical(self, APP_NAME, strings.ERROR_DIALOG.format(message=message))

    def _on_thread_finished(self) -> None:
        self._worker = None

    def _show_summary(self, result: ConvertResult) -> None:
        lines: list[str] = []
        if result.cancelled:
            lines.append(strings.SUMMARY_CANCELLED)
        lines.append(strings.SUMMARY_GENERATED.format(n=result.success_count))
        if result.failed_image_count:
            lines.append(strings.SUMMARY_SKIPPED.format(n=result.failed_image_count))
        if result.job_error_count:
            lines.append(strings.SUMMARY_FAILED_JOBS.format(n=result.job_error_count))

        if result.pdfs:
            lines.append("")
            shown = result.pdfs[:10]
            lines.extend(strings.SUMMARY_ITEM.format(name=p.name) for p in shown)
            if len(result.pdfs) > len(shown):
                lines.append(strings.SUMMARY_MORE.format(n=len(result.pdfs) - len(shown)))

        if not result.results:
            lines = [strings.SUMMARY_EMPTY]

        if result.cancelled:
            self._set_status(strings.STATUS_CANCELLED.format(n=result.success_count))
        else:
            self._set_status(strings.STATUS_DONE.format(n=result.success_count), state="ok")

        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Information)
        box.setText("\n".join(lines))
        box.exec()

    def _open_output(self) -> None:
        if self._last_open_dir and self._last_open_dir.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_open_dir)))

    # -------------------------------------------------------------- update
    def _check_for_update(self) -> None:
        if self._update_check_worker is not None:
            return
        self.btn_update.setEnabled(False)
        self.btn_update.setText(strings.BTN_UPDATE_CHECKING)

        self._update_check_worker = UpdateCheckWorker()
        self._update_check_worker.checked.connect(self._on_update_checked)
        self._update_check_worker.failed.connect(self._on_update_check_failed)
        self._update_check_worker.finished.connect(self._on_update_check_finished)
        self._update_check_worker.start()

    def _reset_update_button(self) -> None:
        self.btn_update.setText(strings.BTN_UPDATE)
        self.btn_update.setEnabled(True)

    def _on_update_check_finished(self) -> None:
        self._update_check_worker = None

    def _on_update_check_failed(self, message: str) -> None:
        self._reset_update_button()
        QMessageBox.warning(self, APP_NAME, strings.UPDATE_CHECK_FAILED.format(message=message))

    def _on_update_checked(self, release: ReleaseInfo | None) -> None:
        self._reset_update_button()
        if release is None:
            QMessageBox.information(self, APP_NAME, strings.UPDATE_NO_RELEASE)
            return
        if not update.is_newer(release.version, __version__):
            QMessageBox.information(
                self, APP_NAME, strings.UPDATE_UP_TO_DATE.format(version=__version__)
            )
            return

        notes = release.notes or "(リリースノートはありません)"
        if len(notes) > 600:
            notes = notes[:600] + "…"
        ret = QMessageBox.question(
            self,
            strings.UPDATE_AVAILABLE_TITLE,
            strings.UPDATE_AVAILABLE_BODY.format(version=release.version, notes=notes),
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        asset = update.pick_windows_asset(release.assets)
        if asset is None:
            QMessageBox.information(self, APP_NAME, strings.UPDATE_NO_ASSET)
            QDesktopServices.openUrl(QUrl(release.html_url))
            return
        self._download_update(asset)

    def _download_update(self, asset: AssetInfo) -> None:
        dest_dir = Path(tempfile.mkdtemp(prefix="imagetopdf_update_"))

        dialog = QProgressDialog(
            strings.UPDATE_DOWNLOADING.format(done="0.0", total="?"),
            strings.UPDATE_PROGRESS_CANCEL,
            0,
            0,
            self,
        )
        dialog.setWindowTitle(strings.UPDATE_PROGRESS_TITLE)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)

        worker = UpdateDownloadWorker(asset, dest_dir)
        self._update_download_worker = worker

        def on_progress(done: int, total: int) -> None:
            if total:
                dialog.setRange(0, total)
                dialog.setValue(min(done, total))
            dialog.setLabelText(
                strings.UPDATE_DOWNLOADING.format(
                    done=f"{done / (1024 * 1024):.1f}",
                    total=f"{total / (1024 * 1024):.1f}" if total else "?",
                )
            )

        def on_completed(path: Path) -> None:
            dialog.close()
            self._offer_install(Path(path))

        def on_cancelled() -> None:
            dialog.close()

        def on_failed(message: str) -> None:
            dialog.close()
            QMessageBox.warning(self, APP_NAME, strings.UPDATE_DOWNLOAD_FAILED.format(message=message))

        def on_thread_finished() -> None:
            self._update_download_worker = None

        worker.progress.connect(on_progress)
        worker.completed.connect(on_completed)
        worker.cancelled.connect(on_cancelled)
        worker.failed.connect(on_failed)
        worker.finished.connect(on_thread_finished)
        dialog.canceled.connect(worker.cancel)

        worker.start()
        dialog.exec()

    def _offer_install(self, installer_path: Path) -> None:
        ret = QMessageBox.question(
            self,
            strings.UPDATE_READY_TITLE,
            strings.UPDATE_READY_BODY.format(app=APP_NAME),
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        try:
            subprocess.Popen([str(installer_path)], close_fds=True)
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, strings.UPDATE_LAUNCH_FAILED.format(message=str(e)))
            return
        self.close()

    # ---------------------------------------------------------- settings I/O
    def _restore_settings(self) -> None:
        s = load_settings()
        o = s.options
        self.seg_mode.setCurrentData(o.mode)
        self.spin_dpi.setValue(max(MIN_DPI, min(MAX_DPI, o.dpi)))
        self.seg_page.setCurrentData(o.page_mode)
        idx = self.cmb_paper.findText(o.paper)
        if idx >= 0:
            self.cmb_paper.setCurrentIndex(idx)
        oi = self.cmb_orient.findData(o.orientation.value)
        if oi >= 0:
            self.cmb_orient.setCurrentIndex(oi)
        if s.last_input_dir and Path(s.last_input_dir).is_dir():
            self._on_folder_chosen(s.last_input_dir)
        self._update_mode_hint()
        self._update_page_controls()
        self._update_output_controls()

    def _current_settings(self) -> Settings:
        try:
            opts = self._build_options()
        except ValueError:
            opts = ConvertOptions()
        return Settings(
            options=opts,
            last_input_dir=str(self._input_dir) if self._input_dir else None,
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        # 変換中なら確認。
        if self._worker and self._worker.isRunning():
            ret = QMessageBox.question(
                self,
                APP_NAME,
                strings.CONFIRM_EXIT,
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                event.ignore()
                return
            self._worker.cancel()
            # キャンセルは画像/ジョブの区切りで効くため数秒かかることがある。
            # wait がタイムアウトしたら、スレッド破棄による異常終了を避けるため
            # 完全に停止するまで待つ（cancel 済みなので必ず終わる）。
            if not self._worker.wait(5000):
                self._set_status(strings.STATUS_CLOSING)
                self._worker.wait()

        # アップデート確認/ダウンロードのスレッドも、破棄前に必ず停止させる
        # （QThread は走行中に破棄すると異常終了するため）。
        if self._update_download_worker and self._update_download_worker.isRunning():
            self._update_download_worker.cancel()
            self._update_download_worker.wait()
        if self._update_check_worker and self._update_check_worker.isRunning():
            self._update_check_worker.wait()

        save_settings(self._current_settings())
        super().closeEvent(event)
