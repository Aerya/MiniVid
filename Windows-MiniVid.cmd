@echo off
setlocal
rem ---- one-file hybrid: batch header + embedded PowerShell ----
set "_ps=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%_ps%" -NoProfile -ExecutionPolicy Bypass -Command ^
  "$self = Get-Content -Raw -LiteralPath '%~f0';" ^
  "$parts = [regex]::Split($self,'(?ms)^\#\s*<PS>\s*$');" ^
  "if($parts.Count -lt 2){Write-Error 'Marker #<PS> not found'; exit 1};" ^
  "Invoke-Expression $parts[1]"
exit /b %errorlevel%

# <PS>
# --------------------- PowerShell part starts here ---------------------

try {
  [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
  [Console]::InputEncoding  = New-Object System.Text.UTF8Encoding($false)
  $null = & chcp.com 65001
} catch {}

# MiniVid bootstrap for Windows - bilingual (EN/FR), guided compose, SMB probe & safe repair
$ErrorActionPreference = 'Stop'

function Info($m){ Write-Host "[i] $m" -ForegroundColor Cyan }
function Ok($m){ Write-Host "[OK] $m" -ForegroundColor Green }
function Warn($m){ Write-Host "[!] $m" -ForegroundColor Yellow }
function Err($m){ Write-Host "[X] $m" -ForegroundColor Red }

try { Unblock-File -Path $PSCommandPath -ErrorAction SilentlyContinue | Out-Null } catch {}

# === Lang & texts ===
$TXT = @{
  en = @{
    title="========== MiniVid Windows Helper =========="
    running="PowerShell {0} running"
    chooseLang="Choose language / Choisir la langue [EN/FR]"
    dockerDetected="Docker detected ({0})."
    installingDocker="Installing Docker Desktop via winget if needed..."
    dockerInstallReq="Docker Desktop install requested."
    startingDD="Starting Docker Desktop..."
    wslRunning='WSL "docker-desktop" is Running; waiting for engine...'
    waitingWSL='Waiting for WSL "docker-desktop" to start...'
    dockerReady="Docker is ready. Using CLI: {0}"
    root="Root"; compose="Compose"; env="Env"
    menu1b="Guided setup (port, folders, SMB volumes)"
    menu2="Install/Update and Start"
    menu3="Restart (quick)"
    menu5="Stop"
    menu6="Open Web UI"
    menu7="Create Desktop shortcut"
    menu8="Generate a fresh compose (with backup)"
    menu9="Remove containers (down)"
    menu11="Remove project images"
    menu12="Configure Web UI auth (user/password)"
    menu0="Exit"
    choice="Choice"
    hintShare="Hint: Docker Desktop > Settings > Resources > File Sharing (share C: if needed)"
    regenBacked="Backed up old compose: {0}"
    regenWrote="Wrote new Windows-friendly compose."
    createdEnv="Created .env: {0}"
    openUrl="Opening {0}"
    shortcutMade="Desktop shortcut created: {0}"
    secUpdated="SECRET_KEY updated in {0}"
    goingDark="Going dark..."
    diagFail="compose config failed. Fix YAML (check your compose/.env)."
    guideTitle="-- Guided docker-compose setup --"
    askPort="Host port for MiniVid (maps to 8080 in container) [default 8080]"
    portBusy="Port {0} seems in use on localhost."
    portUseAnyway="Use it anyway? [y/N]"
    askCount="How many media folders to add? [1-10, default 5]"
    mediaNameN="Display name for folder #{0} (shown in UI)"
    askTypeN="Folder #{0}: Local path (L) or SMB network share (N)? [L/N, default L]"
    askLocalPathN="Windows path for /videos{0} (e.g. C:\Videos\...)"
    askUNCPathN="SMB path for /videos{0} (e.g. \\\\192.168.0.10\\share or //server/share[/sub])"
    askAuthNeeded="Does this SMB share require credentials? [y/N]"
    askCifsUser="CIFS username"
    askCifsPass="CIFS password"
    askCifsDomain="CIFS domain (optional, leave blank if none)"
    willNeedCifs="At least one SMB share detected. CIFS options will be probed."
    probeStart="Probing SMB options for {0} ..."
    probeOK="  [OK] Works with {0}"
    probeFail="  [x] Failed with {0}"
    probeDone="Selected SMB options: {0}"
    savedCompose="Compose updated."
    cleaningVolumes="Cleaning SMB named volumes (they will be recreated)"
    repairing="Repairing CIFS lines in compose..."
    repaired="Compose repaired."
    webAuthEnableQ="Enable Web UI authentication? [y/N]"
    webAuthUserQ="Username"
    webAuthPassQ="Password (input hidden)"
    webAuthOn="Web auth enabled."
    webAuthOff="Web auth disabled."
  }
  fr = @{
    title="========== MiniVid Assistant Windows =========="
    running="PowerShell {0} en cours"
    chooseLang="Choisir la langue / Choose language [FR/EN]"
    dockerDetected="Docker detecte ({0})."
    installingDocker="Installation de Docker Desktop via winget si besoin..."
    dockerInstallReq="Installation de Docker Desktop demandee."
    startingDD="Demarrage de Docker Desktop..."
    wslRunning='WSL "docker-desktop" est demarre; attente du moteur...'
    waitingWSL='En attente du demarrage de WSL "docker-desktop"...'
    dockerReady="Docker pret. CLI utilisee : {0}"
    root="Racine"; compose="Compose"; env="Env"
    menu1b="Assistant de configuration (port, dossiers, volumes SMB)"
    menu2="Installer / Mettre a jour et Demarrer"
    menu3="Redemarrer (rapide)"
    menu5="Arreter"
    menu6="Ouvrir l'interface Web"
    menu7="Creer un raccourci Bureau"
    menu8="Generer un compose vierge (avec sauvegarde)"
    menu9="Supprimer les conteneurs (down)"
    menu11="Supprimer les images du projet"
    menu12="Configurer l'authentification Web (user:mot de passe)"
    menu0="Quitter"
    choice="Choix"
    hintShare="Astuce : Docker Desktop > Settings > Resources > File Sharing (partage C: si besoin)"
    regenBacked="Ancien compose sauvegarde : {0}"
    regenWrote="Compose Windows genere."
    createdEnv=".env cree : {0}"
    openUrl="Ouverture de {0}"
    shortcutMade="Raccourci Bureau cree : {0}"
    secUpdated="SECRET_KEY mis a jour dans {0}"
    goingDark="Ca va faire tout noir !"
    diagFail="Echec de 'compose config'. Corrige le YAML (compose/.env)."
    guideTitle="-- Assistant de remplissage du docker-compose --"
    askPort="Port hote pour MiniVid (mappe vers 8080) [defaut 8080]"
    portBusy="Le port {0} semble deja occupe."
    portUseAnyway="L'utiliser quand meme ? [y/N]"
    askCount="Combien de dossiers medias ajouter ? [1-10, defaut 5]"
    mediaNameN="Nom affiche pour le dossier no {0} (visible dans l'UI)"
    askTypeN="Dossier no {0} : Local (L) ou SMB (N) ? [L/N, defaut L]"
    askLocalPathN="Chemin Windows pour /videos{0} (ex. C:\Videos\...)"
    askUNCPathN="Chemin SMB pour /videos{0} (ex. \\\\192.168.0.10\\share ou //serveur/share[/sous-dossier])"
    askAuthNeeded="Ce partage SMB necessite des identifiants ? [y/N]"
    askCifsUser="Utilisateur CIFS"
    askCifsPass="Mot de passe CIFS"
    askCifsDomain="Domaine CIFS (optionnel)"
    willNeedCifs="Au moins un partage SMB detecte. Test des options CIFS en cours."
    probeStart="Test des options SMB pour {0} ..."
    probeOK="  [OK] Fonctionne avec {0}"
    probeFail="  [x] Echec avec {0}"
    probeDone="Options CIFS retenues : {0}"
    savedCompose="Compose mis a jour."
    cleaningVolumes="Nettoyage des volumes SMB nommes (ils seront recrees)"
    repairing="Reparation des lignes CIFS du compose..."
    repaired="Compose corrige."
    webAuthEnableQ="Activer l'authentification de l'interface Web ? [y/N]"
    webAuthUserQ="Nom d'utilisateur"
    webAuthPassQ="Mot de passe (saisi masque)"
    webAuthOn="Authentification activee."
    webAuthOff="Authentification desactivee."
  }
}
function T($k){ if($Global:LANG -eq 'fr') { return $TXT.fr[$k] } else { return $TXT.en[$k] } }
$choice = (Read-Host (T 'chooseLang'))
if ($choice -match '^(fr|f)$') { $Global:LANG = 'fr' } else { $Global:LANG = 'en' }

# === Paths / constants ===
$Root = Join-Path $env:USERPROFILE 'MiniVid'
$ComposePath = Join-Path $Root 'docker-compose.yml'
$EnvPath     = Join-Path $Root '.env'
$DockerDesktopExe = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
$DockerCliCandidates = @(
  (Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe'),
  'docker'
)

# === Utilities ===
function Find-DockerCli { foreach ($p in $DockerCliCandidates) { try { & $p version *> $null; return $p } catch {} } return $null }
function Ensure-Winget {
  try { Get-Command winget -ErrorAction Stop | Out-Null } catch {
    try { Get-Command winget.exe -ErrorAction Stop | Out-Null } catch {
      Err 'winget not found. Install "App Installer" from Microsoft Store, then re-run.'
      try { Start-Process 'ms-windows-store://pdp/?productid=9NBLGGH4NNS1' | Out-Null } catch {}
      throw 'winget missing'
    }
  }
}
function Ensure-DockerDesktop {
  $cli = Find-DockerCli
  if ($cli) { Ok ([string]::Format((T 'dockerDetected'), $cli)); return }
  Info (T 'installingDocker'); Ensure-Winget
  winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements
  Ok (T 'dockerInstallReq')
}
function Start-DockerAndWait {
  if (Test-Path $DockerDesktopExe) { Info (T 'startingDD'); Start-Process $DockerDesktopExe | Out-Null } else { Warn 'Docker Desktop executable not found.' }
  while ($true) {
    $cli = Find-DockerCli
    if ($cli) { try { & $cli info *> $null; Ok ([string]::Format((T 'dockerReady'), $cli)); return $cli } catch {} }
    try {
      $wsl = & wsl.exe -l -v 2>$null
      if ($wsl -match 'docker-desktop\s+\d+\s+Running') { Info (T 'wslRunning') } else { Info (T 'waitingWSL') }
    } catch {}
    Start-Sleep -Seconds 3
  }
}
function Ensure-Dirs {
  New-Item -ItemType Directory -Force -Path $Root | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $Root 'data')  | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $Root 'cache') | Out-Null
}
function Generate-SecretKey {
  $b = New-Object 'byte[]' 32
  $r = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  $r.GetBytes($b); $r.Dispose()
  ($b | ForEach-Object { $_.ToString('x2') }) -join ''
}
function Set-SecretKey-In-Env {
  param([string]$EnvPath)
  $key = Generate-SecretKey
  if (Test-Path $EnvPath) {
    $raw = Get-Content -Raw $EnvPath
    if ($raw -match '^\s*SECRET_KEY\s*=') { $raw = $raw -replace '^\s*SECRET_KEY\s*=.*$', "SECRET_KEY=$key"; Set-Content -Encoding ASCII -Path $EnvPath -Value $raw }
    else { Add-Content -Path $EnvPath -Encoding ASCII -Value "SECRET_KEY=$key" }
  } else {
    "SECRET_KEY=$key" | Out-File -Encoding ASCII $EnvPath
  }
  Ok ([string]::Format((T 'secUpdated'), $EnvPath)); return $key
}
function Ensure-SecretKey {
  if (-not (Test-Path $EnvPath)) { return }
  $raw = Get-Content -Raw $EnvPath
  if ($raw -notmatch '^\s*SECRET_KEY\s*=\s*\S') { Set-SecretKey-In-Env -EnvPath $EnvPath | Out-Null }
}
function Test-PortInUse([int]$Port){
  try {
    $c = New-Object System.Net.Sockets.TcpClient
    $ar = $c.BeginConnect('127.0.0.1', $Port, $null, $null)
    $ok = $ar.AsyncWaitHandle.WaitOne(200)
    if ($ok) { $c.EndConnect($ar); $c.Close(); return $true } else { $c.Close(); return $false }
  } catch { return $false }
}
function Normalize-Unc([string]$p){
  if (-not $p) { return $p }
  $p = $p.Trim() -replace '\\','/' -replace '^/+','' -replace '/+','/'
  return '//' + $p
}
function PathToForward([string]$p){
  if (-not $p) { return $p }
  $p = $p.Trim().Trim("'`"")
  if ($p -match '^\\\\') { return (Normalize-Unc $p) }
  return ($p -replace '\\','/')
}
function Ensure-Env-Key([string]$key,[string]$val){
  $content = ''
  if (Test-Path $EnvPath) { $content = Get-Content -Raw $EnvPath -ErrorAction SilentlyContinue }
  $pattern = '^\s*' + [regex]::Escape($key) + '\s*=.*$(\r?\n)?'
  $content = [regex]::Replace($content, $pattern, '', [System.Text.RegularExpressions.RegexOptions]::Multiline)
  if ($content -and -not $content.EndsWith("`n")) { $content += "`r`n" }
  $content += ($key + '=' + $val + "`r`n")
  Set-Content -Encoding ASCII -Path $EnvPath -Value $content
}
function Clear-Cifs-Creds {
  $content = ''
  if (Test-Path $EnvPath) { $content = Get-Content -Raw $EnvPath -ErrorAction SilentlyContinue }
  $content = [regex]::Replace($content, '^\s*CIFS_(USER|PASS|DOMAIN)\s*=.*$(\r?\n)?', '',
    [System.Text.RegularExpressions.RegexOptions]::Multiline)
  $content = ($content -split "`r?`n") -join "`r`n"
  $content = $content.TrimEnd() + "`r`n"
  $content += "CIFS_DOMAIN=`r`nCIFS_USER=`r`nCIFS_PASS=`r`n"
  Set-Content -Encoding ASCII -Path $EnvPath -Value $content
}

function Write-DefaultEnv {
@"
APP_URL=http://minivid:8080
MINI_USER=
MINI_PASS=
INTERVAL=3600
CIFS_DOMAIN=
CIFS_USER=
CIFS_PASS=
"@ | Out-File -Encoding ASCII $EnvPath
}
function Detect-OldCompose {
  param([string]$path)
  if (-not (Test-Path $path)) { return $false }
  $txt = Get-Content -Raw -Path $path
  return ($txt -match '^\s*build\s*:' -or $txt -match '/mnt/' -or $txt -match '/etc/localtime' -or $txt -match '/etc/timezone' -or -not ($txt -match 'ghcr\.io/aerya/minivid'))
}
function Backup-And-Write {
  if (Test-Path $ComposePath) {
    $ts = Get-Date -Format 'yyyyMMdd-HHmmss'
    $bak = "$ComposePath.bak-$ts"
    Copy-Item $ComposePath $bak -Force
    Warn ([string]::Format((T 'regenBacked'), $bak))
  }
  Write-DefaultCompose
  Ok (T 'regenWrote')
}
function Ensure-Files {
  Ensure-Dirs
  $regen = $false
  if (-not (Test-Path $ComposePath)) { $regen = $true }
  elseif (Detect-OldCompose -path $ComposePath) { $regen = $true }
  if ($regen) { Backup-And-Write }
  if (-not (Test-Path $EnvPath)) { Write-DefaultEnv; Ok ([string]::Format((T 'createdEnv'), $EnvPath)) }
}
function Open-Editor($file) { Start-Process -FilePath "notepad.exe" -ArgumentList "`"$file`"" }
function Get-HostPort {
  try {
    $m = Select-String -Path $ComposePath -Pattern '^\s*-\s*"?(\d+):8080"' | Select-Object -First 1
    if ($m) { $rx = [regex]'^\s*-\s*"?(\d+):8080"?'; $g = $rx.Match($m.Line).Groups[1].Value; if ($g) { return [int]$g } }
  } catch {}
  return 8080
}

# === Default compose ===
function Write-DefaultCompose {
  $dataHost  = (Join-Path $Root 'data').Replace('\','/')
  $cacheHost = (Join-Path $Root 'cache').Replace('\','/')
  $tpl = @'
services:
  minivid:
    image: ghcr.io/aerya/minivid:latest
    container_name: minivid
    restart: always
    environment:
      TZ: Europe/Paris
      MEDIA_DIRS: /videos1|/videos2|/videos3|/videos4|/videos5
      MEDIA_NAMES: ruTorrent|MeTube|Docs|Concerts|Tests formats video
      DATA_DIR: /data
      THUMB_DIR: /cache/thumbs
      MINI_ALLOWED_EXT: .mp4,.webm,.mkv,.avi,.flv,.m2ts
      MINI_PLAYBACK: auto
      MINI_TRANSCODE: "1"
      MINI_FIREFOX_MKV_FALLBACK: "1"
      MINI_THUMB_OFFSET: "5"
      MINI_THUMB_MAX: "30"
      MINI_AUTOSCAN: "1"
      MINI_USER: ${MINI_USER}
      MINI_PASS: ${MINI_PASS}
      SECRET_KEY: ${SECRET_KEY}
      MINI_BANNED_TAGS: >
        and,the,source,video,videos,vid,vids,film,movie,part,
        les,une,des,ils,elles,sur,sous,dans,par,pour,sans,avec,chez,
        cet,cette,ces,mon,mes,ton,tes,ses,notre,nos,votre,vos,leur,leurs,
        qui,que,quoi,dont,quand,comme,
        your,they,for,with,without,into,onto,about,this,that,these,those,
        here,there,then,than,are,was,being,been,have,had,just,only,
        over,under,very,more,most,less,were,com,net
    volumes:
      - 'C:/CHANGE_ME/rutorrent-direct:/videos1:ro'
      - 'C:/CHANGE_ME/MeTube:/videos2:ro'
      - 'C:/CHANGE_ME/TEST/Docs:/videos3:ro'
      - 'C:/CHANGE_ME/TEST/Concerts:/videos4:ro'
      - 'C:/CHANGE_ME/TEST/Formats:/videos5:ro'
      - '@@DATA_HOST@@:/data'
      - '@@CACHE_HOST@@:/cache'
    ports:
      - "8080:8080"

  minivid-scheduler:
    image: curlimages/curl:8.10.1
    container_name: minivid-scheduler
    depends_on:
      - minivid
    restart: always
    environment:
      APP_URL: ${APP_URL}
      MINI_USER: ${MINI_USER}
      MINI_PASS: ${MINI_PASS}
      INTERVAL: ${INTERVAL}
    command: >
      sh -c '
        set -eu;
        for i in $(seq 1 60); do curl -fsS "$APP_URL/maintenance" >/dev/null 2>&1 && break || sleep 2; done
        while :; do
          if [ -n "$MINI_USER" ] && [ -n "$MINI_PASS" ]; then
            curl -sS -c /tmp/c.jar -X POST "$APP_URL/login" \
              -d "username=$MINI_USER" -d "password=$MINI_PASS" -d "remember=on" -o /dev/null || true
            if curl -sS -b /tmp/c.jar "$APP_URL/api/maintenance/progress" | grep -qi "\"running\"\s*:\s*true"; then
              sleep 120
            else
              curl -m 5 -sS -b /tmp/c.jar -X POST "$APP_URL/api/maintenance/rescan" -o /dev/null || true
            fi
          else
            curl -m 5 -sS -X POST "$APP_URL/api/maintenance/rescan" -o /dev/null || true
          fi
          sleep "$INTERVAL"
        done
      '
'@
  $out = $tpl.Replace('@@DATA_HOST@@', $dataHost).Replace('@@CACHE_HOST@@', $cacheHost)
  Set-Content -Encoding ASCII -Path $ComposePath -Value $out
}

# === Docker wrapper ===
function Invoke-DockerQuiet {
  param([string]$Docker,[string[]]$Args)
  $old = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try { & $Docker @Args 1>$null 2>$null; return $LASTEXITCODE } catch { return 1 } finally { $ErrorActionPreference = $old }
}

# === SMB probe ===
function Probe-CifsOptions {
  param([string]$Docker,[string]$Share,[string]$User,[string]$Pass)
  if ( (Invoke-DockerQuiet -Docker $Docker -Args @('image','inspect','alpine')) -ne 0 ) { $null = Invoke-DockerQuiet -Docker $Docker -Args @('pull','alpine') }
  $combos = @('vers=3.1.1,sec=ntlmssp','vers=3.0,sec=ntlmssp','vers=2.1,sec=ntlmssp','vers=3.1.1','vers=3.0','vers=2.1')
  foreach ($c in $combos) {
    Write-Host ([string]::Format((T 'probeStart'), $Share + " (" + $c + ")"))
    $vol = 'probe_' + ($c -replace '[^0-9A-Za-z]','_')
    $null = Invoke-DockerQuiet -Docker $Docker -Args @('volume','rm', $vol)
    $cmdCreate = @('volume','create','--driver','local','--opt','type=cifs','--opt',"device=$Share",'--opt',("o=username=$User,password=$Pass,file_mode=0777,dir_mode=0777,uid=1000,gid=1000,iocharset=utf8,noperm,$c"),$vol)
    if ( (Invoke-DockerQuiet -Docker $Docker -Args $cmdCreate) -ne 0 ) { Write-Host ((T 'probeFail') -f $c) -ForegroundColor Yellow; continue }
    $cmdRun = @('run','--rm','-v',"$($vol):/mnt",'alpine','sh','-c','ls -la /mnt | head')
    if ( (Invoke-DockerQuiet -Docker $Docker -Args $cmdRun) -eq 0 ) {
      Write-Host ((T 'probeOK') -f $c) -ForegroundColor Green
      $null = Invoke-DockerQuiet -Docker $Docker -Args @('volume','rm',$vol)
      return "file_mode=0777,dir_mode=0777,uid=1000,gid=1000,iocharset=utf8,noperm,$c"
    } else {
      Write-Host ((T 'probeFail') -f $c) -ForegroundColor Yellow
      $null = Invoke-DockerQuiet -Docker $Docker -Args @('volume','rm',$vol)
    }
  }
  return $null
}

# === .env reader for repairs ===
function Read-DotEnv {
  param([string]$Path)
  $map=@{}
  if (Test-Path $Path) {
    $raw = Get-Content -Raw $Path -ErrorAction SilentlyContinue
    foreach($line in ($raw -split "`r?`n")) {
      if ($line -match '^\s*#' -or $line -match '^\s*$') { continue }
      if ($line -match '^\s*([^=\s]+)\s*=\s*(.*)\s*$') { $map[$matches[1]]=$matches[2] }
    }
  }
  return $map
}

# === Prompts ===
function Get-Prompt([string]$key, [int]$i){
  if($Global:LANG -eq 'fr'){
    switch($key){
      'mediaNameN'    { return ("Nom affiche pour le dossier no {0} (visible dans l'UI)" -f $i) }
      'askTypeN'      { return ("Dossier no {0} : Local (L) ou SMB (N) ? [L/N, defaut L]" -f $i) }
      'askLocalPathN' { return ("Chemin Windows pour /videos{0} (ex. C:\Videos\...)" -f $i) }
      'askUNCPathN'   { return ("Chemin SMB pour /videos{0} (ex. \\\\192.168.0.10\\share ou //serveur/share[/sous-dossier])" -f $i) }
    }
  } else {
    switch($key){
      'mediaNameN'    { return ("Display name for folder #{0} (shown in UI)" -f $i) }
      'askTypeN'      { return ("Folder #{0}: Local (L) or SMB (N)? [L/N, default L]" -f $i) }
      'askLocalPathN' { return ("Windows path for /videos{0} (e.g. C:\Videos\...)" -f $i) }
      'askUNCPathN'   { return ("SMB path for /videos{0} (e.g. \\\\192.168.0.10\\share or //server/share[/sub])" -f $i) }
    }
  }
}

# === Guided compose builder ===
function Setup-Compose-Guided {
  param([string]$Docker)
  Write-Host ""; Write-Host (T 'guideTitle') -ForegroundColor Magenta

  # Port
  $port = 8080
  $ans = Read-Host (T 'askPort')
  if ($ans -match '^\d+$') { $p=[int]$ans; if ($p -ge 1 -and $p -le 65535) { $port=$p } }
  if (Test-PortInUse $port) {
    Write-Host ([string]::Format((T 'portBusy'), $port)) -ForegroundColor Yellow
    $use = Read-Host (T 'portUseAnyway')
    if ($use -notmatch '^(y|yes|o|oui)$') {
      do { $ans = Read-Host (T 'askPort'); if ($ans -match '^\d+$') { $p=[int]$ans; if ($p -ge 1 -and $p -le 65535) { $port=$p; break } } } while ($true)
    }
  }

  # Folders
  $count = 5
  $ans = Read-Host (T 'askCount')
  if ($ans -match '^\d+$') { $n=[int]$ans; if ($n -ge 1 -and $n -le 10) { $count=$n } }

  $mediaDirs = @()
  $mediaNames = @()
  $serviceVolumes = New-Object System.Collections.Generic.List[string]
  $cifsBlocks = New-Object System.Collections.Generic.List[string]
  $needsCifs = $false
  $smbPaths = @()
  $authFlags = @()

  for ($i=1; $i -le $count; $i++) {
    $mediaDirs += "/videos$($i)"
    $name = Read-Host (Get-Prompt 'mediaNameN' $i); if (-not $name) { $name = "Folder $i" }
    $mediaNames += $name

    $type = Read-Host (Get-Prompt 'askTypeN' $i)
    if ($type -match '^(n|N)$') {
      $needsCifs = $true
      $unc = Read-Host (Get-Prompt 'askUNCPathN' $i)
      $unc = Normalize-Unc (PathToForward $unc)
      $smbPaths += $unc

      $needAuth = Read-Host (T 'askAuthNeeded')
      $vname = "videos$($i)"
      if ($needAuth -match '^(y|yes|o|oui)$') {
        $serviceVolumes.Add( "      - ${vname}:/videos$($i):ro" ) | Out-Null
        $cifsBlocks.Add( "  ${vname}:`r`n    driver: local`r`n    driver_opts:`r`n      type: cifs`r`n      device: '$unc'`r`n      o: 'username=${CIFS_USER},password=${CIFS_PASS},DOMAINPLACEHOLDER,SECPLACEHOLDER,ro'" ) | Out-Null
        $authFlags += $true
      } else {
        $serviceVolumes.Add( "      - ${vname}:/videos$($i):ro" ) | Out-Null
        $cifsBlocks.Add( "  ${vname}:`r`n    driver: local`r`n    driver_opts:`r`n      type: cifs`r`n      device: '$unc'`r`n      o: 'guest,SECPLACEHOLDER,ro'" ) | Out-Null
        $authFlags += $false
      }
    } else {
      $path = Read-Host (Get-Prompt 'askLocalPathN' $i)
      $path = PathToForward $path
      $serviceVolumes.Add( "      - '$($path):/videos$($i):ro'" ) | Out-Null
    }
  }

  # data/cache local
  $dataHost  = (Join-Path $Root 'data').Replace('\','/')
  $cacheHost = (Join-Path $Root 'cache').Replace('\','/')
  $serviceVolumes.Add( "      - '$($dataHost):/data'" ) | Out-Null
  $serviceVolumes.Add( "      - '$($cacheHost):/cache'" ) | Out-Null

  # SMB creds + probe
  $oTailDefault = "file_mode=0777,dir_mode=0777,uid=1000,gid=1000,iocharset=utf8,noperm,vers=3.1.1,sec=ntlmssp"
  if ($needsCifs) {
    Write-Host (T 'willNeedCifs') -ForegroundColor Yellow
    if (-not (Test-Path $EnvPath)) { Write-DefaultEnv }

    $needAuthAny = ($authFlags | Where-Object { $_ }).Count -gt 0
    $u=$null; $p=$null; $d=$null
    if ($needAuthAny) {
      $u = Read-Host (T 'askCifsUser')
      $p = Read-Host (T 'askCifsPass')
      $d = Read-Host (T 'askCifsDomain')
      if ($u) { Ensure-Env-Key 'CIFS_USER' $u }
      if ($p) { Ensure-Env-Key 'CIFS_PASS' $p }
      if ($d) { Ensure-Env-Key 'CIFS_DOMAIN' $d }
      if (-not $u -and -not $p) {
        for ($j=0; $j -lt $authFlags.Count; $j++) { if ($authFlags[$j]) { $authFlags[$j] = $false } }
      }
    }
    if (-not $needAuthAny) { Clear-Cifs-Creds }

    $uniqShares = $smbPaths | Sort-Object -Unique
    $perShareOpts = @{}
    foreach ($share in $uniqShares) {
      $probeUser = $u; if (-not $probeUser) { $probeUser = 'guest' }
      $probePass = $p; if (-not $probePass) { $probePass = '' }
      $opt = Probe-CifsOptions -Docker $Docker -Share $share -User $probeUser -Pass $probePass
      if (-not $opt) { $opt = $oTailDefault }
      Write-Host ((T 'probeDone') -f $opt) -ForegroundColor Cyan
      $perShareOpts[$share] = $opt
    }

    for ($idx=0; $idx -lt $cifsBlocks.Count; $idx++) {
      $block = $cifsBlocks[$idx]
      $m = [regex]::Match($block, "device:\s*'([^']+)'")
      if ($m.Success) {
        $share = $m.Groups[1].Value
        $opt = $perShareOpts[$share]
        $oline = if (-not $authFlags[$idx]) { "guest,$opt,ro" } else {
          $tmp = "username=${CIFS_USER},password=${CIFS_PASS},"
          if ($d) { $tmp += "domain=${CIFS_DOMAIN}," }
          $tmp + $opt + ",ro"
        }
        $block = [regex]::Replace($block, "o:\s*'[^']*'", "o: '$oline'")
        $cifsBlocks[$idx] = $block
      }
    }
  }

  # write compose
  $serviceJoined = ($serviceVolumes -join "`r`n")
  $tpl = @'
services:
  minivid:
    image: ghcr.io/aerya/minivid:latest
    container_name: minivid
    restart: always
    environment:
      TZ: Europe/Paris
      MEDIA_DIRS: @@MEDIA_DIRS@@
      MEDIA_NAMES: @@MEDIA_NAMES@@
      DATA_DIR: /data
      THUMB_DIR: /cache/thumbs
      MINI_ALLOWED_EXT: .mp4,.webm,.mkv,.avi,.flv,.m2ts
      MINI_PLAYBACK: auto
      MINI_TRANSCODE: "1"
      MINI_FIREFOX_MKV_FALLBACK: "1"
      MINI_THUMB_OFFSET: "5"
      MINI_THUMB_MAX: "30"
      MINI_AUTOSCAN: "1"
      MINI_USER: ${MINI_USER}
      MINI_PASS: ${MINI_PASS}
      SECRET_KEY: ${SECRET_KEY}
      MINI_BANNED_TAGS: >
        and,the,source,video,videos,vid,vids,film,movie,part,
        les,une,des,ils,elles,sur,sous,dans,par,pour,sans,avec,chez,
        cet,cette,ces,mon,mes,ton,tes,ses,notre,nos,votre,vos,leur,leurs,
        qui,que,quoi,dont,quand,comme,
        your,they,for,with,without,into,onto,about,this,that,these,those,
        here,there,then,than,are,was,being,been,have,had,just,only,
        over,under,very,more,most,less,were,com,net
    volumes:
@@SERVICE_VOLUMES@@
    ports:
      - "@@PORT@@:8080"

  minivid-scheduler:
    image: curlimages/curl:8.10.1
    container_name: minivid-scheduler
    depends_on:
      - minivid
    restart: always
    environment:
      APP_URL: ${APP_URL}
      MINI_USER: ${MINI_USER}
      MINI_PASS: ${MINI_PASS}
      INTERVAL: ${INTERVAL}
    command: >
      sh -c '
        set -eu;
        for i in $(seq 1 60); do curl -fsS "$APP_URL/maintenance" >/dev/null 2>&1 && break || sleep 2; done
        while :; do
          if [ -n "$MINI_USER" ] && [ -n "$MINI_PASS" ]; then
            curl -sS -c /tmp/c.jar -X POST "$APP_URL/login" \
              -d "username=$MINI_USER" -d "password=$MINI_PASS" -d "remember=on" -o /dev/null || true
            if curl -sS -b /tmp/c.jar "$APP_URL/api/maintenance/progress" | grep -qi "\"running\"\s*:\s*true"; then
              sleep 120
            else
              curl -m 5 -sS -b /tmp/c.jar -X POST "$APP_URL/api/maintenance/rescan" -o /dev/null || true
            fi
          else
            curl -m 5 -sS -X POST "$APP_URL/api/maintenance/rescan" -o /dev/null || true
          fi
          sleep "$INTERVAL"
        done
      '
'@
  $compose = $tpl.Replace('@@MEDIA_DIRS@@', ($mediaDirs -join '|')).
                 Replace('@@MEDIA_NAMES@@', ($mediaNames -join '|')).
                 Replace('@@SERVICE_VOLUMES@@', $serviceJoined).
                 Replace('@@PORT@@', [string]$port)

  if ($cifsBlocks.Count -gt 0) {
    $compose += "`r`nvolumes:`r`n" + ($cifsBlocks -join "`r`n")
  }

  Set-Content -Encoding ASCII -Path $ComposePath -Value $compose
  Ok (T 'savedCompose')
}

# === Compose CIFS repair (string-only, consult .env) ===
function Repair-ComposeCifs {
  try {
    if (-not (Test-Path $ComposePath)) { return }
    $txt = Get-Content -Raw $ComposePath
    if (-not $txt) { return }
    $orig = $txt

    $txt = $txt -replace "device:\s*'\\\\\\\\", "device: '//"
    $txt = $txt -replace "device:\s*'//+",      "device: '//"
    $txt = [regex]::Replace($txt, "device:\s*'//([^/]+)//", "device: '//$1/")

    $defaultOpts = "file_mode=0777,dir_mode=0777,uid=1000,gid=1000,iocharset=utf8,noperm,vers=3.1.1,sec=ntlmssp"
    $txt = $txt -replace "SECPLACEHOLDER", $defaultOpts
    $txt = $txt -replace "DOMAINPLACEHOLDER,?", ""

    $envMap = Read-DotEnv -Path $EnvPath
    $userEmpty = (-not $envMap.ContainsKey('CIFS_USER')) -or ([string]::IsNullOrWhiteSpace($envMap['CIFS_USER']))
    $passEmpty = (-not $envMap.ContainsKey('CIFS_PASS')) -or ([string]::IsNullOrWhiteSpace($envMap['CIFS_PASS']))
    if ($userEmpty -or $passEmpty) {
      $txt = [regex]::Replace($txt,
        "o:\s*'username=\$\{CIFS_USER\},password=\$\{CIFS_PASS\},[^']*'",
        { param($m)
          $rest = $m.Value -replace "^o:\s*'username=\$\{CIFS_USER\},password=\$\{CIFS_PASS\},",""
          "o: 'guest," + ($rest -replace "^domain=\$\{CIFS_DOMAIN\},","")
        })
    }

    if ($txt -ne $orig) {
      Info (T 'repairing')
      Set-Content -Encoding ASCII -Path $ComposePath -Value $txt
      Ok (T 'repaired')
    }
  } catch {
    Warn ("Repair skipped: " + $_.Exception.Message)
  }
}

# === Purge named SMB volumes (minivid_videosX) ===
function Purge-Smb-NamedVolumes {
  param([string]$Docker)
  try {
    $existing = & $Docker volume ls --format '{{.Name}}' 2>$null
    if (-not $existing) { return }
    if ($existing -isnot [System.Array]) { $existing = ($existing -split "`r?`n") }
    $toRemove = @()
    foreach ($v in $existing) {
      if ($v -match '^minivid_videos\d+$') { $toRemove += $v }
    }
    if ($toRemove.Count -gt 0) {
      Info (T 'cleaningVolumes')
      foreach ($v in $toRemove) { & $Docker volume rm -f $v *> $null }
    }
  } catch {}
}

# === Web UI auth menu ===
function Set-WebAuth {
  if (-not (Test-Path $EnvPath)) { Write-DefaultEnv }
  $ans = Read-Host (T 'webAuthEnableQ')
  if ($ans -match '^(y|yes|o|oui)$') {
    $user = Read-Host (T 'webAuthUserQ')
    $sec  = Read-Host (T 'webAuthPassQ') -AsSecureString
    $ptr  = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    try { $pass = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
    if ([string]::IsNullOrWhiteSpace($user) -or [string]::IsNullOrWhiteSpace($pass)) {
      Warn (T 'webAuthOff'); Ensure-Env-Key 'MINI_USER' ''; Ensure-Env-Key 'MINI_PASS' ''
    } else {
      Ensure-Env-Key 'MINI_USER' $user
      Ensure-Env-Key 'MINI_PASS' $pass
      Ok (T 'webAuthOn')
    }
  } else {
    Ensure-Env-Key 'MINI_USER' ''
    Ensure-Env-Key 'MINI_PASS' ''
    Ok (T 'webAuthOff')
  }
}

# === Compose ops ===
function Compose-Pull-Up {
  param([string]$Docker)

  Ensure-SecretKey
  Repair-ComposeCifs
  & $Docker compose -p minivid -f $ComposePath --env-file $EnvPath down *> $null
  Purge-Smb-NamedVolumes -Docker $Docker

  Info 'validate: docker compose config'
  & $Docker compose -f $ComposePath --env-file $EnvPath config 1>$null 2>$null
  if ($LASTEXITCODE -ne 0) { throw (T 'diagFail') }

  $common = @('compose','-p','minivid','-f',$ComposePath,'--env-file',$EnvPath)

  Info 'docker compose pull'
  & $Docker @common 'pull' '--progress' 'plain'
  if ($LASTEXITCODE -ne 0) {
    Info 'retry: docker compose pull (no --progress)'
    & $Docker @common 'pull'
    if ($LASTEXITCODE -ne 0) { throw 'docker compose pull failed.' }
  }

  Info 'docker compose up -d'
  & $Docker @common 'up' '-d'
  if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed.' }

  Ok 'MiniVid started.'
}

function Open-Web { $p = Get-HostPort; $url = "http://localhost:$p"; Info ([string]::Format((T 'openUrl'), $url)); Start-Process $url | Out-Null }
function Create-Desktop-URL {
  $p = Get-HostPort; $url = "http://localhost:$p"
  $desktop = [Environment]::GetFolderPath('Desktop')
  $file = Join-Path $desktop 'MiniVid.url'
  $content = "[InternetShortcut]`r`nURL=$url`r`n"
  Set-Content -Path $file -Value $content -Encoding ASCII
  Ok ([string]::Format((T 'shortcutMade'), $file))
}
function Confirm { param([string]$msg) $a = Read-Host "$msg [y/N]"; return ($a -match '^(y|yes|o|oui)$') }
function Compose-Stop { param([string]$Docker)
  Info 'docker compose stop'; & $Docker compose -p minivid -f $ComposePath --env-file $EnvPath stop
  if ($LASTEXITCODE -ne 0) { throw 'docker compose stop failed.' } Ok 'Stopped.'
}
function Compose-RestartQuick { param([string]$Docker)
  Info 'docker compose restart'; & $Docker compose -p minivid -f $ComposePath --env-file $EnvPath restart
  if ($LASTEXITCODE -ne 0) { throw 'docker compose restart failed.' } Ok 'Restarted.'
}
function Compose-DownOnly { param([string]$Docker)
  Info 'docker compose down'; & $Docker compose -p minivid -f $ComposePath --env-file $EnvPath down
  if ($LASTEXITCODE -ne 0) { throw 'docker compose down failed.' } Ok 'Containers removed.'
}
function Compose-RemoveImages { param([string]$Docker)
  Info 'detect project images'
  $ids = & $Docker compose -p minivid -f $ComposePath --env-file $EnvPath images --quiet 2>$null | Sort-Object -Unique
  if (-not $ids -or $ids.Count -eq 0) { Warn 'No images found for this project.'; return }
  if (-not ($ids -is [array])) { $ids = @($ids) }
  Write-Host 'Images to remove:' -ForegroundColor Yellow; foreach ($i in $ids) { Write-Host ('  ' + $i) }
  if (-not (Confirm 'Remove these images only?')) { return }
  $failed = @(); foreach ($i in $ids) { & $Docker image rm $i; if ($LASTEXITCODE -ne 0) { $failed += $i } }
  if ($failed.Count -gt 0) { Warn ('Some images could not be removed (in use?): ' + ($failed -join ', ')) } else { Ok 'Project images removed.' }
}

# === Menu (sequential numbering) ===
function Show-Menu {
  Write-Host ""; Write-Host (T 'title') -ForegroundColor Magenta
  Write-Host ((T 'root') + ": " + $Root)
  Write-Host ((T 'compose') + ": " + $ComposePath)
  Write-Host ((T 'env') + ": " + $EnvPath); Write-Host ""
  Write-Host ("1) "  + (T 'menu1b'))
  Write-Host ("2) "  + (T 'menu2'))
  Write-Host ("3) "  + (T 'menu3'))
  Write-Host ("4) "  + (T 'menu5'))
  Write-Host ("5) "  + (T 'menu6'))
  Write-Host ("6) "  + (T 'menu7'))
  Write-Host ("7) "  + (T 'menu8'))
  Write-Host ("8) "  + (T 'menu9'))
  Write-Host ("9) "  + (T 'menu11'))
  Write-Host ("10) " + (T 'menu12'))
  Write-Host ("0) "  + (T 'menu0')); Write-Host ""
}

# ==== Run ====
Write-Host (T 'title') -ForegroundColor Magenta
Info ([string]::Format((T 'running'), $PSVersionTable.PSVersion.ToString()))

function Ensure-Files-Once {
  $Root | Out-Null
  Ensure-Files
}
$cli = Find-DockerCli
if (-not $cli) { Ensure-DockerDesktop; $cli = Start-DockerAndWait } else { Ok ([string]::Format((T 'dockerDetected'), $cli)) }

Ensure-Files

do {
  Show-Menu
  $c = Read-Host (T 'choice')
  switch ($c) {
    '1'  { Setup-Compose-Guided -Docker $cli }
    '2'  { try { Compose-Pull-Up -Docker $cli; Open-Web } catch { Err $_.Exception.Message; Write-Host (T 'hintShare') -ForegroundColor Yellow } }
    '3'  { try { Compose-RestartQuick -Docker $cli } catch { Err $_.Exception.Message } }
    '4'  { try { Compose-Stop -Docker $cli } catch { Err $_.Exception.Message } }
    '5'  { Open-Web }
    '6'  { Create-Desktop-URL }
    '7'  { Backup-And-Write }
    '8'  { try { Compose-DownOnly -Docker $cli } catch { Err $_.Exception.Message } }
    '9'  { try { Compose-RemoveImages -Docker $cli } catch { Err $_.Exception.Message } }
    '10' { try { Set-WebAuth } catch { Err $_.Exception.Message } }
    '0'  { Write-Host ""; Write-Host (T 'goingDark'); $host.SetShouldExit(0); exit }
    Default { Warn 'Invalid choice.' }
  }
} while ($true)

# --------------------- PowerShell part ends here ---------------------
