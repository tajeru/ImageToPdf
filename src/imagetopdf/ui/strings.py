"""UI 文言の一元管理。

技術指示書 §6「将来 i18n 可能なよう文言を一元管理」に対応する。
GUI 層（ui/）で表示する文字列はすべてここに集約する。
core 層が emit する状態メッセージ（走査・変換の進行文言）は
GUI 非依存の責務のため core 側に置いたままとする。
"""
from __future__ import annotations

# --- ヘッダー ---------------------------------------------------------------
TAGLINE = "画像フォルダを、そのままの品質で美しい PDF に。"

# --- ドロップ領域 -----------------------------------------------------------
DROP_TITLE = "フォルダをドラッグ＆ドロップ"
DROP_SUB = "クリックしてフォルダを選択することもできます"
DROP_FORMATS = "対応形式　WEBP ・ PNG ・ JPEG"
DROP_CHANGE_HINT = "クリックまたはドロップで変更できます"

# --- 変換設定 ---------------------------------------------------------------
FIELD_MODE = "変換モード"
FIELD_DPI = "解像度"
FIELD_PAGE = "ページ"
FIELD_OUTPUT = "出力先"

MODE_SINGLE = "1フォルダ → 1PDF"
MODE_SUBFOLDERS = "サブフォルダごとに1PDF"
MODE_HINT_SINGLE = "選択フォルダ直下の画像を 1 つの PDF にまとめます。"
MODE_HINT_SUBFOLDERS = "画像のみの末端フォルダを、それぞれ別の PDF に一括変換します。"

DPI_HINT = "72〜1200 dpi（既定 300）"

PAGE_ORIGINAL = "画像そのまま"
PAGE_FIXED = "用紙サイズに統一"
ORIENT_PORTRAIT = "縦"
ORIENT_LANDSCAPE = "横"
ORIENT_AUTO = "自動"

OUT_SAME = "入力と同じ場所"
OUT_CUSTOM = "指定フォルダ"
BTN_PICK_OUT = "選択…"
OUT_PREFIX = "出力先: {path}"

# --- 操作ボタン -------------------------------------------------------------
BTN_START = "変換開始"
BTN_CANCEL = "キャンセル"
BTN_OPEN_OUTPUT = "出力フォルダを開く"

# --- ダイアログ -------------------------------------------------------------
DLG_PICK_INPUT = "画像フォルダを選択"
DLG_PICK_OUTPUT = "出力先フォルダを選択"
WARN_NO_INPUT = "先に画像フォルダを選択してください。"
WARN_NO_OUTPUT = "出力先フォルダを選択してください。"
ERROR_DIALOG = "変換中にエラーが発生しました:\n{message}"
CONFIRM_EXIT = "変換中です。中断して終了しますか？"

# --- 状態表示 ---------------------------------------------------------------
STATUS_IDLE = "フォルダを選択してください。"
STATUS_READY = "準備完了。［変換開始］を押してください。"
STATUS_STARTED = "変換を開始しました…"
STATUS_PROGRESS = "変換中… {done}/{total} 枚　{name}"
STATUS_CANCELLING = "キャンセル中…（現在の処理が終わると停止します）"
STATUS_DONE = "完了: {n} 件の PDF を生成しました。"
STATUS_CANCELLED = "キャンセル: {n} 件を生成しました。"
STATUS_ERROR = "エラーで停止しました。"
STATUS_CLOSING = "停止処理中… しばらくお待ちください。"

# --- 完了サマリ -------------------------------------------------------------
SUMMARY_CANCELLED = "⚠ キャンセルされました（途中まで生成）。"
SUMMARY_GENERATED = "生成した PDF: {n} 件"
SUMMARY_SKIPPED = "スキップした画像: {n} 枚"
SUMMARY_FAILED_JOBS = "失敗したフォルダ: {n} 件"
SUMMARY_ITEM = "・{name}"
SUMMARY_MORE = "… 他 {n} 件"
SUMMARY_EMPTY = "対象となる画像が見つかりませんでした。"

# --- アップデート -----------------------------------------------------------
BTN_UPDATE = "アップデートを確認"
BTN_UPDATE_CHECKING = "確認中…"
UPDATE_UP_TO_DATE = "お使いのバージョンは最新です（v{version}）。"
UPDATE_NO_RELEASE = "公開されているリリースが見つかりませんでした。"
UPDATE_CHECK_FAILED = "アップデートの確認に失敗しました:\n{message}"
UPDATE_AVAILABLE_TITLE = "アップデートがあります"
UPDATE_AVAILABLE_BODY = "新しいバージョン v{version} が公開されています。\n\n{notes}\n\nダウンロードしますか？"
UPDATE_NO_ASSET = (
    "この環境向けの配布ファイルが見つからなかったため、\n"
    "ブラウザでリリースページを開きます。"
)
UPDATE_DOWNLOADING = "ダウンロード中… {done} / {total} MB"
UPDATE_DOWNLOAD_FAILED = "ダウンロードに失敗しました:\n{message}"
UPDATE_DOWNLOAD_CANCELLED = "ダウンロードをキャンセルしました。"
UPDATE_READY_TITLE = "ダウンロード完了"
UPDATE_READY_BODY = "インストーラーを起動して {app} を終了し、更新を進めますか？"
UPDATE_PROGRESS_TITLE = "アップデートをダウンロード中"
UPDATE_PROGRESS_CANCEL = "キャンセル"
UPDATE_LAUNCH_FAILED = "インストーラーの起動に失敗しました:\n{message}"
