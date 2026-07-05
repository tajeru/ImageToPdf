# ImageToPDF をビルドして配布物を作る一括スクリプト（PowerShell）。
#
# 使い方:  powershell -ExecutionPolicy Bypass -File build\build.ps1
#
# 前提: Inno Setup 6 をインストール済み（ISCC.exe にパスが通っているか、
#       既定の C:\Program Files (x86)\Inno Setup 6\ISCC.exe にある）こと。

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot   # ImageToPDF/
Set-Location $Root

# 1) 仮想環境の用意
if (-not (Test-Path "$Root\.venv")) {
    py -3.12 -m venv "$Root\.venv"
}
$Py = "$Root\.venv\Scripts\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install -r requirements-dev.txt

# 2) テスト
& $Py -m pytest
if ($LASTEXITCODE -ne 0) { throw "テストに失敗しました。ビルドを中止します。" }

# 3) PyInstaller で凍結（dist\ImageToPDF\）
& $Py -m PyInstaller "build\imagetopdf.spec" --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller に失敗しました。" }

# 4) Inno Setup でインストーラー生成（build\Output\ImageToPDF-Setup-*.exe）
$IsccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($Iscc) {
    & $Iscc "build\installer.iss"
    Write-Host "完成: $Root\build\Output\ にインストーラーが生成されました。" -ForegroundColor Green
} else {
    Write-Warning "ISCC.exe が見つかりません。Inno Setup 6 をインストールし、build\installer.iss を手動でコンパイルしてください。"
    Write-Host "凍結済みアプリ: $Root\dist\ImageToPDF\ImageToPDF.exe" -ForegroundColor Green
}
