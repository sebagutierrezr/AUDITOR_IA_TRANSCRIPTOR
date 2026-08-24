#define MyAppName "AUDITOR IA"
#define MyAppVersion "6.1.3"
#define MyAppPublisher "AUDITOR IA"
#define MyAppExeName "AUDITOR_IA.exe"

[Setup]
AppId={{D9896A93-56F3-45AB-B5E3-6C19FF22F060}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AUDITOR IA
DefaultGroupName=AUDITOR IA
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=AUDITOR_IA_6.1.3_Setup
SetupIconFile=..\resources\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

[Files]
Source: "..\dist\AUDITOR_IA_6.1.3_PORTABLE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AUDITOR IA"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AUDITOR IA"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir AUDITOR IA"; Flags: nowait postinstall skipifsilent
