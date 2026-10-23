; Inno Setup 6 Script for SENTRON Windows Desktop Application
; Produces dist\installer\SENTRON_Setup.exe
; Per-user installation to {localappdata}\Programs\SENTRON without admin elevation required.
; Preserves all user data in {localappdata}\SENTRON across upgrades and uninstallation.

#define MyAppName "SENTRON"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SENTRON Security"
#define MyAppURL "https://github.com/HonnappaSwamyTN/SENTRON"
#define MyAppExeName "SENTRON.exe"

[Setup]
AppId={{8B15F05A-2CD9-4D88-9B92-7E55AA5E0251}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=SENTRON_Setup
SetupIconFile=assets\sentron.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
CloseApplications=force
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Explicitly install application icon to {app}\sentron.ico for system shortcuts
Source: "assets\sentron.ico"; DestDir: "{app}"; Flags: ignoreversion
; Distribute only the PyInstaller build output. Never include databases or settings.
Source: "..\dist\SENTRON\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\sentron.ico"; Comment: "SENTRON Local Security Guard for AI Actions and System Stability"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\sentron.ico"; Tasks: desktopicon; Comment: "SENTRON Local Security Guard for AI Actions and System Stability"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove only installation files, never touching {localappdata}\SENTRON where user SQLite databases and settings reside
Type: filesandordirs; Name: "{app}"
