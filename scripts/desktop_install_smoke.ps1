# Runs exclusively on disposable GitHub-hosted Windows runners.
# All environment changes below are forbidden on developer machines.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'Installation smoke test is restricted to GitHub-hosted disposable runners.'
}
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$evidenceDir = Join-Path $repoRoot '.desktop-build/evidence'
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
$installer = Get-ChildItem -LiteralPath (Join-Path $repoRoot 'desktop/src-tauri/target/release/bundle/nsis') -Filter '*-setup.exe' | Select-Object -First 1
if (-not $installer) { throw 'Installer missing' }
$installTarget = Join-Path $env:LOCALAPPDATA 'Facetmark CI 中文 Test'
$dataTarget = Join-Path $env:RUNNER_TEMP 'Facetmark CI 资料库'
$env:FACETMARK_DATA_DIR = $dataTarget
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9223'
$env:FACETMARK_CI_WEBVIEW_INSPECT = '1'
$env:FACETMARK_CI_FAIL_WORKSPACE_ONCE = '1'
$env:FACETMARK_CI_EVIDENCE_DIR = $evidenceDir
$env:FACETMARK_CI_TRAY_INSPECT = '1'
$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
Get-ChildItem Env: | Where-Object Name -Like 'PYTHON*' | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }

# Remove the preinstalled runtime on this disposable VM, then prove it absent.
$runtimeRoots = @("${env:ProgramFiles(x86)}\Microsoft\EdgeWebView\Application", "$env:ProgramFiles\Microsoft\EdgeWebView\Application", "$env:LOCALAPPDATA\Microsoft\EdgeWebView\Application")
foreach ($root in $runtimeRoots) {
    if (Test-Path -LiteralPath $root) {
        $setups = Get-ChildItem -LiteralPath $root -Filter setup.exe -Recurse -ErrorAction SilentlyContinue
        foreach ($setup in $setups) {
            $arguments = @('--uninstall', '--msedgewebview', '--force-uninstall', '--verbose-logging')
            if (-not $root.StartsWith($env:LOCALAPPDATA)) { $arguments += '--system-level' }
            $p = Start-Process -FilePath $setup.FullName -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
        }
    }
}
$remaining = @($runtimeRoots | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { Get-ChildItem -LiteralPath $_ -Filter msedgewebview2.exe -Recurse -ErrorAction SilentlyContinue })
if ($remaining.Count -gt 0) { throw 'Cannot prove WebView2 absent on this runner; offline-install gate remains unverified.' }

# Keep the Actions agent online, block outbound network for all installers/apps.
$firewallGroup = 'Facetmark offline installation test'
$blockedPrograms = @($installer.FullName, (Join-Path $installTarget 'facetmark-desktop.exe'), (Join-Path $installTarget 'facetmark-service.exe'), "${env:ProgramFiles(x86)}\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe")
foreach ($program in $blockedPrograms) {
    New-NetFirewallRule -DisplayName "Facetmark offline $([IO.Path]::GetFileName($program))" -Group $firewallGroup -Direction Outbound -Program $program -Action Block | Out-Null
}
try {
    # NSIS /D must be last and must not be quoted, even when it contains spaces.
    $installed = Start-Process -FilePath $installer.FullName -ArgumentList "/S /D=$installTarget" -Wait -PassThru -WindowStyle Hidden
    if ($installed.ExitCode -ne 0) { throw "Installer failed: $($installed.ExitCode)" }
    $exe = Join-Path $installTarget 'facetmark-desktop.exe'
    if (-not (Test-Path -LiteralPath $exe)) { throw "Installed application missing: $exe" }
    Add-Type -AssemblyName System.Drawing
    $installedIcon = [System.Drawing.Icon]::ExtractAssociatedIcon($exe)
    if (-not $installedIcon) { throw 'Installed executable has no application icon.' }
    $installedIconBitmap = $installedIcon.ToBitmap()
    $installedIconBitmap.Save((Join-Path $evidenceDir 'installed-app-icon.png'), [System.Drawing.Imaging.ImageFormat]::Png)
    @{ commit = $env:GITHUB_SHA; source = 'Icon extracted from the installed executable'; width = $installedIconBitmap.Width; height = $installedIconBitmap.Height } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceDir 'installed-app-icon.json') -Encoding utf8
    $installedIconBitmap.Dispose()
    $installedIcon.Dispose()
    $app = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
    & (Join-Path $repoRoot '.desktop-build/venv/Scripts/python.exe') (Join-Path $repoRoot 'scripts/installed_window_check.py') $evidenceDir startup $app.Id
    if ($LASTEXITCODE -ne 0) { throw 'Installed startup failure did not recover through its real keyboard retry.' }
    $manifest = Join-Path $dataTarget 'desktop-runtime.json'
    $deadline = (Get-Date).AddSeconds(60)
    do {
        Start-Sleep -Milliseconds 500
        if ($app.HasExited) { throw 'Desktop process exited during startup' }
    } while (-not (Test-Path -LiteralPath $manifest) -and (Get-Date) -lt $deadline)
    if (-not (Test-Path -LiteralPath $manifest)) { throw 'Installed desktop never started its backend' }
    $ready = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$($ready.port)/health"
    if (-not $health.ok) { throw 'Installed backend is unhealthy' }
    # WebView2 must actually be running, not merely present in a registry key.
    $webviews = @(Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" | Where-Object { $_.CommandLine -like '*facetmark*' })
    if ($webviews.Count -eq 0) { throw 'No Facetmark WebView2 process started' }
    # Attach to this installed app's WebView, not a separately launched browser.
    $webviews | Select-Object ProcessId, ParentProcessId, CommandLine | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceDir 'webview-processes.json') -Encoding utf8
    & (Join-Path $repoRoot '.desktop-build/venv/Scripts/python.exe') (Join-Path $repoRoot 'scripts/installed_webview_check.py') $evidenceDir
    if ($LASTEXITCODE -ne 0) { throw 'Installed WebView interaction check failed; inspect its trace and evidence.' }
    & (Join-Path $repoRoot '.desktop-build/venv/Scripts/python.exe') (Join-Path $repoRoot 'scripts/installed_tray_check.py') $evidenceDir $app.Id operate
    if ($LASTEXITCODE -ne 0) { throw 'Installed tray actions, keyboard and focus checks failed.' }
    $token = (Get-Content -LiteralPath (Join-Path $dataTarget 'pairing-token.txt') -Raw).Trim()
    $headers = @{ Authorization = "Bearer $token" }
    $saved = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$($ready.port)/bookmark" -Headers $headers -ContentType 'application/json' -Body '{"url":"https://ci.example/retained","title":"Synthetic retained bookmark"}'
    $report = @{ installer_bytes = $installer.Length; installed_path = $installTarget; runtime_absent_before = $true; network_blocked_for_installers = $true; backend_ready = $true; webview_processes = $webviews.Count; signed = ((Get-AuthenticodeSignature -LiteralPath $installer.FullName).Status -eq 'Valid') }
    $report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceDir 'installed-desktop.json') -Encoding utf8
    & (Join-Path $repoRoot '.desktop-build/venv/Scripts/python.exe') (Join-Path $repoRoot 'scripts/installed_window_check.py') $evidenceDir prepare $app.Id
    if ($LASTEXITCODE -ne 0) { throw 'Native drag persistence and final close flush failed.' }
    Stop-Process -Id $app.Id
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Process -Id $ready.pid -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 300 }
    if (Get-Process -Id $ready.pid -ErrorAction SilentlyContinue) { throw 'Backend survived parent exit' }
    $env:FACETMARK_CI_FAIL_WORKSPACE_ONCE = '0'
    $app = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
    & (Join-Path $repoRoot '.desktop-build/venv/Scripts/python.exe') (Join-Path $repoRoot 'scripts/installed_window_check.py') $evidenceDir restored $app.Id
    if ($LASTEXITCODE -ne 0) { throw 'Native geometry did not restore its physical frame into the monitor work area.' }
    $ready = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    & (Join-Path $repoRoot '.desktop-build/venv/Scripts/python.exe') (Join-Path $repoRoot 'scripts/installed_tray_check.py') $evidenceDir $app.Id exit
    if ($LASTEXITCODE -ne 0) { throw 'Tray Quit did not stop the relaunched desktop and its owned service.' }
    if (-not $app.WaitForExit(30000)) { throw 'Relaunched desktop did not exit through its tray menu.' }
    # A same-version reinstall is a repair smoke; it is not a cross-version upgrade test.
    $repair = Start-Process -FilePath $installer.FullName -ArgumentList "/S /D=$installTarget" -Wait -PassThru -WindowStyle Hidden
    if ($repair.ExitCode -ne 0) { throw 'Same-version reinstall failed' }
    $dbFile = Join-Path $dataTarget 'facetmark.db'
    if (-not (Test-Path -LiteralPath $dbFile)) { throw 'Reinstall removed the user database' }
    $uninstaller = Join-Path $installTarget 'uninstall.exe'
    if (-not (Test-Path -LiteralPath $uninstaller)) { throw 'NSIS uninstaller missing' }
    $uninstall = Start-Process -FilePath $uninstaller -ArgumentList '/S' -Wait -PassThru -WindowStyle Hidden
    if ($uninstall.ExitCode -ne 0) { throw 'Uninstall failed' }
    if (-not (Test-Path -LiteralPath $dbFile)) { throw 'Uninstall removed user data' }
    if ((Get-Content -LiteralPath (Join-Path $dataTarget 'pairing-token.txt') -Raw).Trim() -ne $token) { throw 'Pairing changed during uninstall' }
    @{ same_version_reinstall = $true; uninstall_kept_data = $true; backend_stopped_with_parent = $true; synthetic_bookmark_id = $saved.bookmark_id } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceDir 'lifecycle.json') -Encoding utf8
} catch {
    # Capture the disposable runner's desktop when CDP is unavailable, so a
    # startup error and a WebView inspection failure can be distinguished.
    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $capture = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($capture)
        $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
        $capture.Save((Join-Path $evidenceDir 'runner-failure.png'))
        $graphics.Dispose()
        $capture.Dispose()
        Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*facetmark*' -or $_.Name -in @('msedgewebview2.exe', 'msedge.exe', 'chrome.exe', 'powershell.exe', 'explorer.exe') } | Select-Object ProcessId, ParentProcessId, Name, CommandLine | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceDir 'failure-processes.json') -Encoding utf8
    } catch { Write-Warning "Failure evidence unavailable: $_" }
    throw
} finally {
    Get-NetFirewallRule -Group $firewallGroup -ErrorAction SilentlyContinue | Remove-NetFirewallRule
}
