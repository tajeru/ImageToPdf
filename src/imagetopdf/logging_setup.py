"""ログ設定。%LOCALAPPDATA%\\ImageToPDF\\logs\\app.log にローテーション出力。"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import logs_dir

_configured = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """ルートロガーを一度だけ構成する。"""
    global _configured
    logger = logging.getLogger("imagetopdf")
    if _configured:
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ファイル出力（書き込めない環境でも落ちないよう try）。
    try:
        d = logs_dir()
        d.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            d / "app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass

    # コンソール出力（開発時の確認用）。
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    _configured = True
    return logger


def get_logger(name: str = "imagetopdf") -> logging.Logger:
    return logging.getLogger(name)
