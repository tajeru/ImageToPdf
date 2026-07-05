"""GitHub Releases を使ったアップデート確認・ダウンロード。

GUI 非依存（core 直下）。公開リポジトリの Releases API を認証なしで
読み取るだけなので、トークン等は一切必要ない。

- fetch_latest_release() : 最新リリース情報を取得（未公開なら None）
- is_newer()              : バージョン文字列を比較
- pick_windows_asset()    : 配布アセットから Windows 用インストーラーを選ぶ
- download_asset()        : アセットを進捗付きでダウンロード
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import GITHUB_REPO

_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_HEADERS = {
    "User-Agent": "ImageToPDF-Updater",
    "Accept": "application/vnd.github+json",
}
_CHUNK = 65536

ProgressCb = Callable[[int, int], None]
CancelCb = Callable[[], bool]


class UpdateCheckError(Exception):
    """アップデート確認（GitHub API 呼び出し）に失敗。"""


class UpdateDownloadError(Exception):
    """アセットのダウンロードに失敗。"""


class UpdateDownloadCancelled(Exception):
    """ダウンロードがキャンセルされた。"""


@dataclass
class AssetInfo:
    name: str
    url: str
    size: int = 0


@dataclass
class ReleaseInfo:
    tag: str
    version: str
    name: str
    notes: str
    html_url: str
    assets: list[AssetInfo] = field(default_factory=list)


def _strip_v(text: str) -> str:
    return text[1:] if text[:1] in ("v", "V") else text


def _parse_version(text: str) -> tuple[int, ...]:
    nums: list[int] = []
    for part in _strip_v(text).strip().split("."):
        m = re.match(r"\d+", part)
        nums.append(int(m.group()) if m else 0)
    return tuple(nums) or (0,)


def is_newer(remote_version: str, local_version: str) -> bool:
    """remote_version が local_version より新しいか（解析不能時は False）。"""
    try:
        r = _parse_version(remote_version)
        l = _parse_version(local_version)
    except Exception:
        return False
    n = max(len(r), len(l))
    r = r + (0,) * (n - len(r))
    l = l + (0,) * (n - len(l))
    return r > l


def fetch_latest_release(timeout: float = 6.0) -> ReleaseInfo | None:
    """最新リリースを取得する。公開リリースが無ければ None。

    Raises:
        UpdateCheckError: ネットワークエラー・API エラー。
    """
    req = Request(_API_LATEST, headers=_HEADERS)
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 - 固定の https API URL
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return None
        raise UpdateCheckError(f"GitHub API エラー（HTTP {e.code}）") from e
    except URLError as e:
        raise UpdateCheckError(str(e.reason)) from e
    except Exception as e:  # noqa: BLE001
        raise UpdateCheckError(str(e)) from e

    assets = [
        AssetInfo(
            name=a.get("name", ""),
            url=a.get("browser_download_url", ""),
            size=int(a.get("size") or 0),
        )
        for a in data.get("assets", [])
    ]
    tag = data.get("tag_name", "")
    return ReleaseInfo(
        tag=tag,
        version=_strip_v(tag),
        name=data.get("name") or tag,
        notes=(data.get("body") or "").strip(),
        html_url=data.get("html_url", ""),
        assets=assets,
    )


# インストーラー（Setup 系 exe）を優先し、無ければ任意の exe を探す。
_INSTALLER_RE = re.compile(r"(?i)setup.*\.exe$")
_EXE_RE = re.compile(r"(?i)\.exe$")


def pick_windows_asset(assets: list[AssetInfo]) -> AssetInfo | None:
    """配布アセットから Windows 用インストーラーを選ぶ（無ければ None）。"""
    for a in assets:
        if _INSTALLER_RE.search(a.name):
            return a
    for a in assets:
        if _EXE_RE.search(a.name):
            return a
    return None


def download_asset(
    asset: AssetInfo,
    dest_dir: Path,
    on_progress: ProgressCb | None = None,
    should_cancel: CancelCb | None = None,
) -> Path:
    """アセットを dest_dir へダウンロードし、書き出したパスを返す。

    Raises:
        UpdateDownloadCancelled: キャンセルされた場合。
        UpdateDownloadError: ダウンロードに失敗した場合。
    """
    on_progress = on_progress or (lambda done, total: None)
    should_cancel = should_cancel or (lambda: False)

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / asset.name

    req = Request(asset.url, headers=_HEADERS)
    try:
        with urlopen(req, timeout=15) as resp:  # noqa: S310 - GitHub リリースアセット URL
            total = int(resp.headers.get("Content-Length") or asset.size or 0)
            done = 0
            with dest.open("wb") as f:
                while True:
                    if should_cancel():
                        raise UpdateDownloadCancelled()
                    chunk = resp.read(_CHUNK)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    on_progress(done, total)
    except UpdateDownloadCancelled:
        dest.unlink(missing_ok=True)
        raise
    except Exception as e:  # noqa: BLE001
        dest.unlink(missing_ok=True)
        raise UpdateDownloadError(str(e)) from e

    return dest
