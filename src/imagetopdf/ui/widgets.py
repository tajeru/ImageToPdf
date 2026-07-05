"""カスタムウィジェット群（テーマ対応の再利用部品）。

- FolderDropArea   : クリック / D&D でフォルダを受け取るヒーロー領域
- SegmentedControl : ラジオボタン代替のセグメント切替
- ElidedLabel      : 幅に応じて省略表示するラベル
- logo_pixmap      : ヘッダー用ロゴマーク（QPainter 描画・任意 DPI 対応）

配色は ui/theme.py のトークンを参照し、QSS で表現できない装飾
（破線ボーダーのグローアニメーション等）のみ QPainter で描く。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from . import strings, theme


# ---------------------------------------------------------------- ElidedLabel
class ElidedLabel(QLabel):
    """幅が足りないときに省略記号（…）で切り詰めるラベル。

    setText ではなく setFullText を使う。レイアウトを押し広げないよう
    最小幅を 0 として扱う。
    """

    def __init__(self, text: str = "", parent=None, mode: Qt.TextElideMode = Qt.ElideMiddle) -> None:
        super().__init__(parent)
        self._full = text or ""
        self._mode = mode
        self._refresh()

    def setFullText(self, text: str) -> None:
        self._full = text or ""
        self._refresh()

    def fullText(self) -> str:
        return self._full

    def minimumSizeHint(self):  # noqa: N802
        hint = super().minimumSizeHint()
        hint.setWidth(0)
        return hint

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        width = max(24, self.width() - 2)
        self.setText(self.fontMetrics().elidedText(self._full, self._mode, width))


# ----------------------------------------------------------- SegmentedControl
class SegmentedControl(QFrame):
    """排他選択のセグメント切替（QRadioButton の代替）。

    addSegment(text, data) で選択肢を追加し、currentData() で選択中の
    data を得る。選択が変わると dataChanged(data) を emit する。
    """

    dataChanged = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("cls", "segmented")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idToggled.connect(self._on_toggled)
        self._data: list[object] = []

    def addSegment(self, text: str, data: object) -> QPushButton:  # noqa: N802
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setProperty("cls", "segment")
        index = len(self._data)
        self._data.append(data)
        self._group.addButton(btn, index)
        self.layout().addWidget(btn)
        if index == 0:
            btn.setChecked(True)
        return btn

    def currentData(self) -> object:  # noqa: N802
        index = self._group.checkedId()
        return self._data[index] if index >= 0 else None

    def setCurrentData(self, data: object) -> None:  # noqa: N802
        for index, d in enumerate(self._data):
            if d == data:
                self._group.button(index).setChecked(True)
                return

    def _on_toggled(self, index: int, checked: bool) -> None:
        if checked:
            self.dataChanged.emit(self._data[index])


# ------------------------------------------------- 矢印付き入力（QSS 対応）
def _draw_chevron(painter: QPainter, cx: float, cy: float, *, up: bool, enabled: bool) -> None:
    """幅約 9px の山形矢印を (cx, cy) 中心に描く。"""
    color = QColor(theme.SUB if enabled else theme.FAINT)
    pen = QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    dy = -2.2 if up else 2.2
    painter.drawPolyline(QPolygonF([
        QPointF(cx - 4.2, cy - dy),
        QPointF(cx, cy + dy),
        QPointF(cx + 4.2, cy - dy),
    ]))


class ComboBox(QComboBox):
    """下向き矢印を自前描画するコンボボックス。

    QSS で ::drop-down を装飾すると標準矢印が描かれなくなるため、
    paintEvent でテーマ色の矢印を描き足す。
    """

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        _draw_chevron(
            painter,
            self.width() - 13.0,
            self.height() / 2.0,
            up=False,
            enabled=self.isEnabled(),
        )


class SpinBox(QSpinBox):
    """上下ボタンの矢印を自前描画するスピンボックス（ComboBox と同じ理由）。"""

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx = self.width() - 11.0
        _draw_chevron(painter, cx, self.height() * 0.32, up=True, enabled=self.isEnabled())
        _draw_chevron(painter, cx, self.height() * 0.68, up=False, enabled=self.isEnabled())


# ------------------------------------------------------------- アイコン描画
def _folder_glyph(rect: QRectF) -> QPainterPath:
    """タブ付きフォルダのシルエットパス。"""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    radius = w * 0.10
    path = QPainterPath()
    path.addRoundedRect(QRectF(x, y + h * 0.12, w * 0.44, h * 0.30), radius * 0.6, radius * 0.6)
    body = QPainterPath()
    body.addRoundedRect(QRectF(x, y + h * 0.24, w, h * 0.64), radius, radius)
    return path.united(body)


def _accent_gradient(rect: QRectF) -> QLinearGradient:
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor(theme.ACCENT))
    grad.setColorAt(0.6, QColor(theme.ACCENT2))
    grad.setColorAt(1.0, QColor(theme.ACCENT3))
    return grad


def _make_canvas(size: int, dpr: float) -> tuple[QPixmap, QPainter]:
    pm = QPixmap(round(size * dpr), round(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    return pm, painter


def logo_pixmap(size: int, dpr: float = 1.0) -> QPixmap:
    """角丸グラデーションタイル + 白抜きフォルダのロゴマーク。"""
    pm, p = _make_canvas(size, dpr)
    rect = QRectF(0, 0, size, size)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_accent_gradient(rect)))
    p.drawRoundedRect(rect, size * 0.28, size * 0.28)

    inner = rect.adjusted(size * 0.24, size * 0.27, -size * 0.24, -size * 0.23)
    white = QColor("#FFFFFF")
    white.setAlpha(242)
    p.setBrush(white)
    p.drawPath(_folder_glyph(inner))
    p.end()
    return pm


def folder_pixmap(size: int, dpr: float = 1.0, *, selected: bool = False, opacity: float = 1.0) -> QPixmap:
    """ドロップ領域用フォルダアイコン。selected でチェックバッジ付きになる。"""
    pm, p = _make_canvas(size, dpr)
    p.setOpacity(opacity)
    area = QRectF(size * 0.06, size * 0.06, size * 0.88, size * 0.88)

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_accent_gradient(area)))
    p.drawPath(_folder_glyph(area))

    # 上辺の淡いハイライトで立体感を出す。
    highlight = QColor("#FFFFFF")
    highlight.setAlpha(34)
    p.setBrush(highlight)
    p.drawRoundedRect(
        QRectF(area.x() + area.width() * 0.07, area.y() + area.height() * 0.28,
               area.width() * 0.86, area.height() * 0.10),
        size * 0.03, size * 0.03,
    )

    # 右下バッジ（未選択: ↓ / 選択済み: チェック）。
    d = size * 0.36
    bx = area.right() - d * 0.82
    by = area.bottom() - d * 0.82
    ring = QColor(theme.SURFACE)
    p.setBrush(ring)
    p.drawEllipse(QRectF(bx - size * 0.045, by - size * 0.045, d + size * 0.09, d + size * 0.09))
    p.setBrush(QColor(theme.OK) if selected else QColor(theme.HOVER))
    p.drawEllipse(QRectF(bx, by, d, d))

    pen = QPen(
        QColor("#FFFFFF") if selected else QColor(theme.SUB),
        max(2.0, size * 0.045),
        Qt.SolidLine,
        Qt.RoundCap,
        Qt.RoundJoin,
    )
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    cx, cy = bx + d / 2, by + d / 2
    if selected:
        p.drawPolyline(QPolygonF([
            QPointF(cx - d * 0.22, cy + d * 0.02),
            QPointF(cx - d * 0.05, cy + d * 0.19),
            QPointF(cx + d * 0.24, cy - d * 0.16),
        ]))
    else:
        p.drawLine(QPointF(cx, cy - d * 0.20), QPointF(cx, cy + d * 0.14))
        p.drawPolyline(QPolygonF([
            QPointF(cx - d * 0.14, cy + d * 0.01),
            QPointF(cx, cy + d * 0.16),
            QPointF(cx + d * 0.14, cy + d * 0.01),
        ]))
    p.end()
    return pm


# -------------------------------------------------------------- FolderDropArea
class FolderDropArea(QFrame):
    """フォルダを受け取るヒーロー領域。

    - フォルダの D&D で folderDropped(str) を emit
    - クリック / Space / Enter で clicked を emit（選択ダイアログ起動用）
    - ドラッグ中は破線ボーダーがグラデーションに変わるグローアニメーション
    """

    folderDropped = Signal(str)
    clicked = Signal()

    _RADIUS = 16.0
    _MARGIN = 5.0  # グロー描画分の余白

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumHeight(196)
        self._selected: str | None = None
        self._pressed = False

        self._glow = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_glow)

        self._icon = QLabel()
        self._icon.setAlignment(Qt.AlignCenter)
        self._title = QLabel()
        self._title.setProperty("cls", "dropTitle")
        self._title.setAlignment(Qt.AlignCenter)
        self._sub = ElidedLabel()
        self._sub.setProperty("cls", "dropSub")
        self._sub.setAlignment(Qt.AlignCenter)
        self._meta = QLabel()
        self._meta.setProperty("cls", "dropMeta")
        self._meta.setAlignment(Qt.AlignCenter)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 16)
        lay.setSpacing(4)
        lay.addStretch(1)
        lay.addWidget(self._icon)
        lay.addSpacing(8)
        lay.addWidget(self._title)
        lay.addWidget(self._sub)
        lay.addStretch(1)
        lay.addWidget(self._meta)

        self.show_selection(None)

    # ------------------------------------------------------------ 表示状態
    def show_selection(self, folder: str | None) -> None:
        """選択中フォルダの表示を更新する（None でプレースホルダーに戻す）。"""
        self._selected = folder or None
        if folder:
            path = Path(folder)
            self._title.setText(path.name or str(path))
            self._sub.setFullText(str(path))
            self._meta.setText(strings.DROP_CHANGE_HINT)
        else:
            self._title.setText(strings.DROP_TITLE)
            self._sub.setFullText(strings.DROP_SUB)
            self._meta.setText(strings.DROP_FORMATS)
        self._update_icon()
        self.update()

    def _update_icon(self) -> None:
        pm = folder_pixmap(
            64,
            self.devicePixelRatioF(),
            selected=bool(self._selected),
            opacity=1.0 if self.isEnabled() else 0.38,
        )
        self._icon.setPixmap(pm)

    # ------------------------------------------------------------ D&D
    @staticmethod
    def _first_folder(event) -> str | None:
        md = event.mimeData()
        if not md.hasUrls():
            return None
        for url in md.urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                return str(p)
        return None

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self.isEnabled() and self._first_folder(event):
            event.acceptProposedAction()
            self._animate_glow(1.0)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._animate_glow(0.0)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        folder = self._first_folder(event)
        self._animate_glow(0.0)
        if folder:
            event.acceptProposedAction()
            self.folderDropped.emit(folder)
        else:
            event.ignore()

    # ------------------------------------------------------------ クリック
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.isEnabled():
            self._pressed = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if (
            self._pressed
            and event.button() == Qt.LeftButton
            and self.isEnabled()
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit()
        self._pressed = False
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if self.isEnabled() and event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.clicked.emit()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------ 再描画契機
    def enterEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().focusOutEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802
        if event.type() == event.Type.EnabledChange:
            self._update_icon()
            self.update()
        super().changeEvent(event)

    # ------------------------------------------------------------ グロー
    def _animate_glow(self, target: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(target)
        self._anim.start()

    def _on_glow(self, value) -> None:
        self._glow = float(value)
        self.update()

    # ------------------------------------------------------------ 描画
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        m = self._MARGIN
        rect = QRectF(self.rect()).adjusted(m, m, -m, -m)
        t = self._glow
        enabled = self.isEnabled()
        hovered = enabled and self.underMouse()

        # 背景（ドラッグ中はアクセント方向へわずかに色づく）。
        if not enabled:
            bg = QColor(theme.WELL)
        elif t > 0:
            bg = theme.blend(theme.SURFACE, theme.ACCENT, 0.07 * t)
        elif hovered:
            bg = theme.blend(theme.SURFACE, "#FFFFFF", 0.025)
        else:
            bg = QColor(theme.SURFACE)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, self._RADIUS, self._RADIUS)

        # 外周グロー（ドラッグ中のみ）。
        if t > 0:
            halo = QColor(theme.ACCENT2)
            halo.setAlphaF(0.22 * t)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(halo, 7))
            painter.drawRoundedRect(rect, self._RADIUS, self._RADIUS)

        # 破線ボーダー。通常色とグラデーションを t でクロスフェードする。
        dash = [4.0, 3.2]
        painter.setBrush(Qt.NoBrush)
        if t < 1.0:
            if not enabled:
                color = QColor(theme.BORDER_SOFT)
            elif hovered or self.hasFocus():
                color = QColor(theme.DASH)
            else:
                color = QColor("#2F3A4C")
            color.setAlphaF(color.alphaF() * (1.0 - t))
            pen = QPen(color, 1.6)
            pen.setCapStyle(Qt.RoundCap)
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern(dash)
            painter.setPen(pen)
            painter.drawRoundedRect(rect, self._RADIUS, self._RADIUS)
        if t > 0:
            grad = QLinearGradient(rect.topLeft(), rect.topRight())
            for pos, name in ((0.0, theme.ACCENT), (0.5, theme.ACCENT2), (1.0, theme.ACCENT3)):
                color = QColor(name)
                color.setAlphaF(t)
                grad.setColorAt(pos, color)
            pen = QPen(QBrush(grad), 1.8 + 0.6 * t)
            pen.setCapStyle(Qt.RoundCap)
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern(dash)
            painter.setPen(pen)
            painter.drawRoundedRect(rect, self._RADIUS, self._RADIUS)
