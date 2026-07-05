; Inno Setup スクリプト — ImageToPDF
;
; 前提: PyInstaller で dist\ImageToPDF\ を生成済みであること。
;   cd ImageToPDF
;   pyinstaller build\imagetopdf.spec --noconfirm
; その後このスクリプトを Inno Setup Compiler で開いてビルドすると
;   Output\ImageToPDF-Setup-1.0.exe が生成される。

#define MyAppName "ImageToPDF"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "img2pdf project"
#define MyAppExeName "ImageToPDF.exe"

[Setup]
AppId={{8B3D1C2E-6A41-4E7C-9F2A-IMG2PDF00001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=ImageToPDF-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\resources\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; 管理者権限が無くてもユーザー領域へインストールできるようにする。
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller の onedir 出力をまるごと取り込む。
Source: "..\dist\ImageToPDF\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
