; =============================================================================
; TubeArchive Pro  |  Version 2.3.2  |  build\installer.iss      (Inno Setup 6, compile with build\build.bat)
; What the wizard does: language of the wizard (English, Arabic, French, German, Spanish, Portuguese, Russian, Turkish + Chinese / Hindi
; when their .isl files are in build\) -> program languages (English + Arabic always, the others optional) -> welcome -> licenses -> folder ->
; shortcuts -> installs the program + tools (yt-dlp, ffmpeg, ffprobe) + texts/languages/default settings -> launch.
; At start it asks GitHub for the newest release and offers to download it first (installer_settings.iss: GitHubRepo).
; User data (settings, history ...) lives in %APPDATA%\TubeArchivePro and is kept on upgrade; the uninstaller asks.
; =============================================================================
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#include "installer_settings.iss"
#define MyAppExe "TubeArchivePro.exe"

[Setup]
AppId={{4BDA0F7B-0977-4171-B957-C944B9F75992}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyPublisher}
AppPublisherURL={#MyWebsite}
AppSupportURL={#MyWebsite}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
OutputDir=output
OutputBaseFilename=TubeArchivePro_Setup_{#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
LicenseFile=LICENSES.txt
InfoBeforeFile=INSTALL_INFO.txt
CloseApplications=yes
RestartApplications=no
#if FileExists(SourcePath + "TubeArchivePro.ico")
SetupIconFile=TubeArchivePro.ico
#endif

[Languages]
; the first question of the setup (Inno Setup shows the list when there is more than one). English and Arabic first.
Name: "english"; MessagesFile: "compiler:Default.isl"
#if FileExists(SourcePath + "Arabic.isl")
Name: "arabic"; MessagesFile: "Arabic.isl"
#endif
#if FileExists(SourcePath + "ChineseSimplified.isl")
Name: "chinese"; MessagesFile: "ChineseSimplified.isl"
#endif
#if FileExists(SourcePath + "Hindi.isl")
Name: "hindi"; MessagesFile: "Hindi.isl"
#endif
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Types]
Name: "default"; Description: "English + Arabic (recommended)"
Name: "all"; Description: "All languages"
Name: "custom"; Description: "Choose the languages"; Flags: iscustom

[Components]
Name: "program"; Description: "TubeArchive Pro"; Types: default all custom; Flags: fixed
Name: "lang_en"; Description: "English"; Types: default all custom; Flags: fixed
Name: "lang_ar"; Description: "العربية (Arabic)"; Types: default all custom; Flags: fixed
Name: "lang_zh"; Description: "中文 (Chinese)"; Types: all
Name: "lang_hi"; Description: "हिन्दी (Hindi)"; Types: all
Name: "lang_es"; Description: "Español (Spanish)"; Types: all
Name: "lang_fr"; Description: "Français (French)"; Types: all
Name: "lang_pt"; Description: "Português (Portuguese)"; Types: all
Name: "lang_ru"; Description: "Русский (Russian)"; Types: all
Name: "lang_de"; Description: "Deutsch (German)"; Types: all
Name: "lang_tr"; Description: "Türkçe (Turkish)"; Types: all

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; the program (PyInstaller one-folder build)
Source: "dist\TubeArchivePro\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; helper programs
Source: "..\tools\yt-dlp.exe"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "..\tools\ffmpeg.exe"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "..\tools\ffprobe.exe"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "..\tools\ffplay.exe"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist
; texts, pictures, languages, default settings (read only; the program writes its data in %APPDATA%\TubeArchivePro)
Source: "..\assets\info\*"; DestDir: "{app}\assets\info"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\assets\sounds\*"; DestDir: "{app}\assets\sounds"; Flags: recursesubdirs createallsubdirs ignoreversion skipifsourcedoesntexist
Source: "..\assets\owner\*"; DestDir: "{app}\assets\owner"; Flags: recursesubdirs createallsubdirs ignoreversion skipifsourcedoesntexist
; language files: English + Arabic always; the other languages only when ticked (the program lists what is installed)
Source: "..\data\languages\en.json"; DestDir: "{app}\data\languages"; Flags: ignoreversion; Components: lang_en
Source: "..\data\languages\ar.json"; DestDir: "{app}\data\languages"; Flags: ignoreversion; Components: lang_ar
Source: "..\data\languages\zh.json"; DestDir: "{app}\data\languages"; Flags: ignoreversion; Components: lang_zh
Source: "..\data\languages\hi.json"; DestDir: "{app}\data\languages"; Flags: ignoreversion; Components: lang_hi
Source: "..\data\languages\es.json"; DestDir: "{app}\data\languages"; Flags: ignoreversion; Components: lang_es
Source: "..\data\languages\fr.json"; DestDir: "{app}\data\languages"; Flags: ignoreversion; Components: lang_fr
Source: "..\data\languages\pt.json"; DestDir: "{app}\data\languages"; Flags: ignoreversion; Components: lang_pt
Source: "..\data\languages\ru.json"; DestDir: "{app}\data\languages"; Flags: ignoreversion; Components: lang_ru
Source: "..\data\languages\de.json"; DestDir: "{app}\data\languages"; Flags: ignoreversion; Components: lang_de
Source: "..\data\languages\tr.json"; DestDir: "{app}\data\languages"; Flags: ignoreversion; Components: lang_tr
Source: "..\data\config\default_settings.json"; DestDir: "{app}\data\config"; Flags: ignoreversion
Source: "..\data\downloads_baseline.txt"; DestDir: "{app}\data"; Flags: ignoreversion
Source: "..\data\splash_baseline.json"; DestDir: "{app}\data"; Flags: ignoreversion
Source: "LICENSES.txt"; DestDir: "{app}"; Flags: ignoreversion
#if FileExists(SourcePath + "redist\vc_redist.x64.exe")
Source: "redist\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: VCRedistNeeded
#endif

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
#if FileExists(SourcePath + "redist\vc_redist.x64.exe")
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Microsoft Visual C++ runtime..."; Check: VCRedistNeeded; Flags: waituntilterminated
#endif
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
{ ---------------- Microsoft Visual C++ runtime (needed by Qt on a clean Windows) ---------------- }
function VCRedistNeeded(): Boolean;
var Installed: Cardinal;
begin
  Result := True;
  if RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) then
    Result := (Installed <> 1);
end;

{ ---------------- check for a newer release on GitHub when the setup starts ---------------- }
function JsonString(const Json, Key: String): String;
var P, Q: Integer; Rest: String;
begin
  Result := '';
  P := Pos('"' + Key + '"', Json);
  if P = 0 then Exit;
  Rest := Copy(Json, P + Length(Key) + 2, 200);
  P := Pos(':', Rest);
  if P = 0 then Exit;
  Rest := Copy(Rest, P + 1, 200);
  P := Pos('"', Rest);
  if P = 0 then Exit;
  Rest := Copy(Rest, P + 1, 200);
  Q := Pos('"', Rest);
  if Q = 0 then Exit;
  Result := Copy(Rest, 1, Q - 1);
end;

function NewerReleaseOnline(var Tag, Page: String): Boolean;
var Http: Variant; Json, Ver: String; Mine, Theirs: Int64;
begin
  Result := False;
  try
    Http := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    Http.Open('GET', 'https://api.github.com/repos/{#GitHubRepo}/releases/latest', False);
    Http.SetRequestHeader('User-Agent', 'TubeArchivePro-Setup');
    Http.SetTimeouts(4000, 4000, 4000, 6000);
    Http.Send('');
    if Http.Status <> 200 then Exit;
    Json := Http.ResponseText;
    Tag := JsonString(Json, 'tag_name');
    Page := JsonString(Json, 'html_url');
    Ver := Tag;
    if (Length(Ver) > 0) and ((Ver[1] = 'v') or (Ver[1] = 'V')) then Delete(Ver, 1, 1);
    if StrToVersion('{#MyAppVersion}', Mine) and StrToVersion(Ver, Theirs) then
      Result := ComparePackedVersion(Theirs, Mine) > 0;
  except
    Result := False;      { offline / blocked: the setup simply goes on }
  end;
end;

function InitializeSetup(): Boolean;
var Tag, Page: String; I: Integer; Skip: Boolean; ErrorCode: Integer;
begin
  Result := True;
  Skip := WizardSilent or ('{#GitHubRepo}' = 'OWNER/REPO');
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), '/SKIPUPDATECHECK') = 0 then Skip := True;
  if Skip then Exit;
  if NewerReleaseOnline(Tag, Page) then
    if MsgBox('A newer version of {#MyAppName} is available online (' + Tag + '). This setup installs {#MyAppVersion}.' + #13#10 + #13#10 +
              'Open the download page now?  (Yes = open the page and close this setup, No = continue with this version)' + #13#10 + #13#10 +
              'يوجد إصدار أحدث من البرنامج على الإنترنت (' + Tag + '). هل تريد فتح صفحة التحميل؟',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      if Page = '' then Page := 'https://github.com/{#GitHubRepo}/releases/latest';
      ShellExec('open', Page, '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
      Result := False;
    end;
end;

{ ---------------- the language chosen in the wizard becomes the language of the program (first install only) ---------------- }
function ProgramLanguage(): String;
begin
  Result := 'en';
  if ActiveLanguage = 'arabic' then Result := 'ar'
  else if (ActiveLanguage = 'chinese') and WizardIsComponentSelected('lang_zh') then Result := 'zh'
  else if (ActiveLanguage = 'hindi') and WizardIsComponentSelected('lang_hi') then Result := 'hi'
  else if (ActiveLanguage = 'spanish') and WizardIsComponentSelected('lang_es') then Result := 'es'
  else if (ActiveLanguage = 'french') and WizardIsComponentSelected('lang_fr') then Result := 'fr'
  else if (ActiveLanguage = 'portuguese') and WizardIsComponentSelected('lang_pt') then Result := 'pt'
  else if (ActiveLanguage = 'russian') and WizardIsComponentSelected('lang_ru') then Result := 'ru'
  else if (ActiveLanguage = 'german') and WizardIsComponentSelected('lang_de') then Result := 'de'
  else if (ActiveLanguage = 'turkish') and WizardIsComponentSelected('lang_tr') then Result := 'tr';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var Dir, F: String;
begin
  if CurStep = ssPostInstall then
  begin
    Dir := ExpandConstant('{userappdata}\TubeArchivePro\data\config');
    F := Dir + '\current_settings.json';
    if not FileExists(F) then
    begin
      ForceDirectories(Dir);
      SaveStringToFile(F, '{"language": "' + ProgramLanguage() + '"}', False);
    end;
  end;
end;

{ ---------------- uninstall: keep or delete the user data ---------------- }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var Dir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Dir := ExpandConstant('{userappdata}\TubeArchivePro');
    if DirExists(Dir) and (not UninstallSilent) then
      if MsgBox('Also delete your settings, favorites, history and downloaded ads?' + #13#10 + Dir + #13#10 + #13#10 +
                '(Your downloaded videos are never deleted.)', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(Dir, True, True, True);
  end;
end;
