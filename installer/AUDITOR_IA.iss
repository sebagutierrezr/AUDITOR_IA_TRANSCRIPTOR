#define MyAppName "AUDITOR IA - TRANSCRIPTOR"
#define MyAppVersion "8.1.0"
#define MyAppExeName "AUDITOR_IA.exe"

[Setup]
AppId={{A4EAC7A3-1DD9-4C0E-9C13-AUDITORIA800}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\AUDITOR IA
DefaultGroupName=AUDITOR IA
OutputDir=..\release
OutputBaseFilename=AUDITOR_IA_8.1.0_Setup
Compression=lzma2/ultra64
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
AppPublisher=AUDITOR IA
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\resources\logo.ico
PrivilegesRequired=admin
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\AUDITOR_IA_8.1.0_BUILD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AUDITOR IA"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AUDITOR IA"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir AUDITOR IA"; Flags: nowait postinstall skipifsilent
