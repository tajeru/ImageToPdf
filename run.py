"""PyInstaller 用のエントリスクリプト（src レイアウトを sys.path に追加）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from imagetopdf.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
