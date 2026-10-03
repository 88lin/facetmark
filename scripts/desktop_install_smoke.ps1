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
    $app = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
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
    $report = @{ installer_bytes = $installer.Length; installed_path = $installTarget; runtime_absent_before = $true; network_blocked_for_installers = $true; backend_ready = $true; webview_processes = $webviews.Count; signed = ((Get-AuthenticodeSignature -LiteralPath $installer.FullName).Status -eq 'Valid') }
    $report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceDir 'installed-desktop.json') -Encoding utf8
    Stop-Process -Id $app.Id
} finally {
    Get-NetFirewallRule -Group $firewallGroup -ErrorAction SilentlyContinue | Remove-NetFirewallRule
}
