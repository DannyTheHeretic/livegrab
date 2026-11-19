; Per-user Livegrab installer.
; Before compiling, put these four files in packaging\build\windows:
;   Livegrab.exe  yt-dlp.exe  ffmpeg.exe  ffprobe.exe
; Compile with ISCC.exe packaging\livegrab.iss

#define MyAppName "Livegrab"
#define MyAppVersion "0.1.0"
#define MyAppExeName "Livegrab.exe"

[Setup]
AppId={{A7E4C91B-2D58-4F63-9A10-6C8B5E2F4D71}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Livegrab
DefaultDirName={localappdata}\Livegrab
DefaultGroupName=Livegrab
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=build\output
OutputBaseFilename=Livegrab-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "build\windows\Livegrab.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\windows\yt-dlp.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\windows\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\windows\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start Livegrab"; Flags: nowait postinstall skipifsilent
