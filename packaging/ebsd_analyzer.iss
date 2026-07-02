; ============================================================================
;  Inno Setup script for EBSD Analyzer  (Windows installer / Setup.exe)
;
;  What the user does:  double-click Setup.exe -> Next -> Next -> Finish.
;  During install it copies the app, then runs install.bat which fetches a
;  private conda-forge environment (via pixi) next to the app. A Start Menu
;  and Desktop shortcut launch the GUI. No Python/conda/admin needed by the
;  user; pixi is local to the install folder and uninstalls cleanly.
;
;  Build this installer with Inno Setup 6 (free, https://jrsoftware.org/isdl.php):
;     "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ebsd_analyzer.iss
;  Run ISCC from the standalone_ebsd\packaging folder (paths are relative to it).
; ============================================================================

#define AppName "EBSD Analyzer"
#define AppVersion "1.0.0"
#define AppPublisher "Jaemyun"
#define AppExeName "launch.bat"

[Setup]
AppId={{8F3A6C21-EB5D-4A9A-9E31-EBSD0ANALYZER}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\EBSD_Analyzer
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; per-user install (no admin prompt); flip to admin if you prefer Program Files
PrivilegesRequired=lowest
OutputBaseFilename=EBSD_Analyzer_Setup
OutputDir=Output
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; the app itself is CPU-only; no special arch requirement beyond x64
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; --- application code (the source tree, minus dev/build artifacts) ---------
; Source paths are relative to this .iss file (packaging\), so ".." = standalone_ebsd
Source: "..\app.py";              DestDir: "{app}"; Flags: ignoreversion
Source: "..\worker.py";           DestDir: "{app}"; Flags: ignoreversion
Source: "..\pixi.toml";           DestDir: "{app}"; Flags: ignoreversion
Source: "..\pixi.lock";           DestDir: "{app}"; Flags: ignoreversion
Source: "..\install.bat";         DestDir: "{app}"; Flags: ignoreversion
Source: "..\get_pixi.ps1";        DestDir: "{app}"; Flags: ignoreversion
Source: "..\launch.bat";          DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md";           DestDir: "{app}"; Flags: ignoreversion
Source: "..\ebsd_engine\*";       DestDir: "{app}\ebsd_engine"; Flags: ignoreversion recursesubdirs
Source: "..\ui\*";                DestDir: "{app}\ui";          Flags: ignoreversion recursesubdirs
Source: "..\gsh_core\*";          DestDir: "{app}\gsh_core";    Flags: ignoreversion recursesubdirs

[Run]
; Fetch the environment during install, shown as a wizard step. The user waits
; on this once (needs internet). /C keeps the console; StatusMsg tells them why.
Filename: "{app}\install.bat"; StatusMsg: "Downloading analysis components (one-time, needs internet)..."; Flags: runascurrentuser waituntilterminated

[Icons]
Name: "{group}\{#AppName}";        Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";  Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[UninstallDelete]
; remove the fetched environment + local pixi so nothing is left behind
Type: filesandordirs; Name: "{app}\.pixi"
Type: filesandordirs; Name: "{app}\.pixi-bin"
Type: filesandordirs; Name: "{app}\__pycache__"
