"""テスト共通設定。src レイアウトを import 可能にし、画像生成ヘルパーを提供。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _make_image(
    path: Path,
    size: tuple[int, int] = (100, 150),
    color=(220, 60, 60),
    mode: str = "RGB",
    fmt: str | None = None,
) -> Path:
    path = Path(path)
    img = Image.new(mode, size, color)
    img.save(path, format=fmt)
    return path


@pytest.fixture
def make_image():
    return _make_image
