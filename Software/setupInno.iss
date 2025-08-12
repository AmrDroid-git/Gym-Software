#define MyAppName "Gym Software"
#define MyAppVersion "1.0.0"
#define MyPublisher "Your Name"
#define MyExeName "GymSoftware.exe"

[Setup]
AppId={{6E3C1A0E-0B7D-4B3F-8E6F-7F4F1E0D9A31}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableDirPage=no
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=GymSoftwareSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Files]
; Main app (onedir)
Source: "dist\GymSoftware\*"; DestDir: "{app}\GymSoftware"; Flags: recursesubdirs createallsubdirs
; One-time DB initializer
Source: "dist\InitializeGymData.exe"; DestDir: "{app}"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\GymSoftware\{#MyExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\GymSoftware\{#MyExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
; Create DB only if it doesn't exist in Documents\GymSoftware
Filename: "{app}\InitializeGymData.exe"; \
    Flags: runhidden waituntilterminated; \
    Check: not FileExists(ExpandConstant('{userdocs}\GymSoftware\gym.db'))

; Launch app after install (optional)
Filename: "{app}\GymSoftware\{#MyExeName}"; \
    Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
