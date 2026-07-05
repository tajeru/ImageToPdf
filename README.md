# ImageToPDF

WEBP / PNG / JPEG の画像が入ったフォルダを選ぶだけで PDF に変換する Windows 向け GUI アプリです。
既存の `convert_and_generate_pdf.bat`（ZIP ドラッグ＆ドロップ + ffmpeg/mogrify/img2pdf）を、
外部 exe 不要・フォルダ選択方式・GUI 付きに置き換えたものです。

技術設計の詳細は [`../技術指示書.md`](../技術指示書.md) を参照してください。

## できること

- **フォルダを選ぶ／ドラッグ＆ドロップ**して画像を 1 つの PDF にまとめる
- 2 つの変換モード
  - **1フォルダ → 1PDF**：選択フォルダ直下の画像をまとめて 1 PDF
  - **サブフォルダごとに1PDF**：画像のみのフォルダ（サブフォルダを持たない末端）をそれぞれ別 PDF に一括変換
- 対応形式：**WEBP / PNG / JPEG**（アニメ WEBP は先頭フレームのみ）
- **DPI 設定**（既定 300）
- **ページサイズ**：「画像そのまま（等倍）」/「用紙に統一（A4 など・縦/横/自動）」
- 既存 PDF があっても**上書きせず連番**（`name_1.pdf`）で保存。**元画像・元フォルダは削除しません**
- **モダンなダークテーマ UI**：グラデーションアクセント・ドラッグ中のグロー表示・
  クリックでも選択できるドロップ領域・Windows タイトルバーのダーク化
- **バージョン表示 / アップデート確認**：画面右上に現在のバージョンを常時表示。
  ［アップデートを確認］から GitHub の最新リリースをチェックし、新しい配布ファイル
  （インストーラー exe）があればアプリ内でダウンロード → インストーラー起動まで行える

> HEIC / AVIF / GIF は初版では非対応です（将来対応予定）。

## 並び順について

ページの並びは**ファイル名順（自然順）**です。数字部分を数値として比較するため、
ゼロ埋めしていない連番（`1, 2, …, 10, 11`）でも正しい順序になります
（`01, 02, …` のようなゼロ埋めでも同じく正しく並びます）。

---

## 開発環境での実行

```powershell
# 1. 仮想環境
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 依存インストール（開発用）
pip install -r requirements-dev.txt

# 3. 起動
python run.py
#   または  python -m imagetopdf  （src を PYTHONPATH に通している場合）

# 4. テスト
pytest
```

## ビルド（配布物の作成）

### 一括スクリプト
```powershell
powershell -ExecutionPolicy Bypass -File build\build.ps1
```
テスト → PyInstaller 凍結 → （Inno Setup があれば）インストーラー生成まで行います。

### 手動手順
```powershell
# 凍結（dist\ImageToPDF\ImageToPDF.exe が生成される）
pip install pyinstaller
pyinstaller build\imagetopdf.spec --noconfirm

# インストーラー（Inno Setup 6 が必要。Output\ImageToPDF-Setup-1.0.0.exe）
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\installer.iss
```

### コード署名について（重要）
配布インストーラーは**未署名**です。そのため初回実行時に Windows SmartScreen の
「WindowsによってPCが保護されました」という警告が出ることがあります。その場合は
**［詳細情報］→［実行］** で続行できます（技術指示書の方針 A=未署名で運用）。
社内配布などで警告を消したい場合はコード署名証明書での署名を検討してください。

---

## アップデート確認の仕組み

- アプリ右上の「v1.0.0」表示の隣にある **［アップデートを確認］** を押すと、
  GitHub の `https://github.com/tajeru/ImageToPdf` の **最新 Release** を問い合わせます
  （公開リポジトリの読み取り専用 API のため認証不要）。
- 現在のバージョンより新しいタグが見つかった場合、リリースノートを表示し、
  ダウンロードするか確認します。同意すると、Release に添付された Windows 用
  インストーラー（`*Setup*.exe`）をアプリ内でダウンロードし、完了後に
  「インストーラーを起動して終了しますか？」と確認したうえで起動・自動終了します。
- Release にインストーラー資産が無い場合は、ブラウザで Release ページを開くだけの
  安全なフォールバックになります。
- **新バージョンをリリースする側の運用**：`git tag vX.Y.Z && git push origin vX.Y.Z`
  でタグを付け、GitHub の Releases 画面からそのタグを選んで Release を公開し、
  `build\build.ps1` で生成したインストーラー `.exe` を Release にアセットとして
  添付してください。アセットが無いと「アップデートあり」までは通知されますが、
  自動ダウンロードは行われません（ブラウザでの手動ダウンロードに切り替わります）。

---

## プロジェクト構成

```
ImageToPDF/
├── run.py                       # 起動エントリ（PyInstaller のターゲット）
├── pyproject.toml               # パッケージ定義 / pytest 設定
├── requirements*.txt
├── src/imagetopdf/
│   ├── app.py                   # QApplication 起動
│   ├── config.py                # 既定値・ConvertOptions・設定の保存/読込
│   ├── logging_setup.py         # ログ（%LOCALAPPDATA%\ImageToPDF\logs）
│   ├── worker.py                # QThread ワーカー（変換・アップデート確認/DL）
│   ├── core/                    # GUI 非依存の変換ロジック
│   │   ├── scanner.py           # フォルダ走査・ジョブ列挙
│   │   ├── decoder.py           # デコード・正規化（白背景合成など）
│   │   ├── pdf_builder.py       # img2pdf による PDF 生成（DPI/用紙）
│   │   ├── converter.py         # 上記を束ねる・進捗/キャンセル
│   │   └── update.py            # GitHub Releases 照会・アセット選定・ダウンロード
│   └── ui/
│       ├── theme.py             # デザイントークン・QSS（ダークテーマ）・ダークタイトルバー
│       ├── strings.py           # UI 文言の一元管理（将来の i18n 準備）
│       ├── widgets.py           # ドロップ領域・セグメント切替等のカスタム部品
│       └── main_window.py       # メイン画面（セクション別ビルダーで構成）
├── tests/                       # pytest（core を中心に 18 ケース）
├── build/
│   ├── imagetopdf.spec          # PyInstaller 設定
│   ├── installer.iss            # Inno Setup スクリプト
│   └── build.ps1                # 一括ビルド
└── resources/                   # アイコン（app.ico を置く）
```

## ライセンス / サードパーティ

- 本体: MIT
- 依存: PySide6 (LGPL v3) / Pillow (HPND) / img2pdf (LGPL)

配布時はサードパーティのライセンス表記を同梱してください。
