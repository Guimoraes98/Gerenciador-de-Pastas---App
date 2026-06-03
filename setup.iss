; =============================================================
;  setup.iss — Inno Setup Script
;  Gera: EfitecSolarSetup_v1.0.0.exe
;
;  Como usar:
;  1. Compile: pyinstaller efitecsolar.spec
;  2. Abra este arquivo no Inno Setup Compiler e clique Build
;  3. O instalador aparece em Output/
; =============================================================

#define AppName    "Efitecsolar - Gerenciador de Pastas"
#define AppVersion "1.1.3"
#define AppExeName "Efitecsolar.exe"
#define AppPublisher "Efitecsolar"

[Setup]
AppId={{A3F7B2C1-4D8E-4F9A-B1C2-D3E4F5A6B7C8}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL=https://github.com/Guimoraes98/Gerenciador-de-Pastas---App
AppSupportURL=https://github.com/Guimoraes98/Gerenciador-de-Pastas---App
AppUpdatesURL=https://github.com/Guimoraes98/Gerenciador-de-Pastas---App/releases
DefaultDirName={localappdata}\Efitecsolar
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=EfitecSolarSetup_v{#AppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na Área de Trabalho"; GroupDescription: "Ícones adicionais:"; Flags: unchecked

[Files]
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";         Filename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar";         Filename: "{uninstallexe}"
Name: "{commondesktop}\Efitecsolar"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Executar {#AppName}"; Flags: nowait postinstall skipifsilent
