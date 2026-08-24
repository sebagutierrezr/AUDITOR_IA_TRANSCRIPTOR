#define MyAppName "AUDITOR IA - TRANSCRIPTOR"
#define MyAppVersion "7.0.0"
#define MyAppPublisher "AUDITOR IA"
#define MyAppExeName "AUDITOR_IA.exe"

[Setup]
AppId={{7BCA8B45-563B-4BC9-9C77-7A0D17007000}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\AUDITOR IA
DefaultGroupName=AUDITOR IA
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=AUDITOR_IA_7.0.0_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\resources\logo.ico
UninstallDisplayIcon={app}\AUDITOR_IA.exe
VersionInfoVersion=7.0.0.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\dist\AUDITOR_IA_7.0.0_APP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AUDITOR IA"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AUDITOR IA"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir AUDITOR IA"; Flags: nowait postinstall skipifsilent
