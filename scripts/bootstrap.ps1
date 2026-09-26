#Requires -Version 5.1
[CmdletBinding()]
param(
    [switch] $Source,
    [switch] $Plan,
    [string] $Target = 'local',
    [string] $Root = (Split-Path -Parent $PSScriptRoot),
    [switch] $PublishAliases
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '../bootstrap/windows.ps1')
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::Is64BitProcess -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') {
    throw 'Native bootstrap requires Windows x64 and 64-bit Windows PowerShell 5.1; ARM64 is not supported.'
}
Assert-NativeLocation $Root $true
$Root = [IO.Path]::GetFullPath($Root)
if ($Target -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid target name.' }
$pins = Get-Content -LiteralPath (Join-Path $Root 'bootstrap/windows.json') -Raw | ConvertFrom-Json
if ($pins.schema -ne 1 -or $pins.platform -cne 'Windows-x64') { throw 'Unsupported native pin schema/platform.' }
foreach ($name in @('uv','mise','python')) {
    if ($pins."${name}_version" -notmatch '^\d+\.\d+\.\d+$' -or $pins."${name}_sha256" -cnotmatch '^[a-f0-9]{64}$') { throw 'Invalid prerequisite version/digest.' }
    Assert-HttpsUrl $pins."${name}_url"
}
$homeDirectory = if ($env:AI_DLC_BOOTSTRAP_HOME) { $env:AI_DLC_BOOTSTRAP_HOME } else { Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ai-dlc/bootstrap' }
Assert-NativeLocation $homeDirectory
$homeDirectory = [IO.Path]::GetFullPath($homeDirectory)
$mode = if ($Source) { 'source' } else { 'release' }
$manifest = $null
$manifestBytes = $null
$manifestPath = Join-Path $Root 'bootstrap/release.sh'
if (-not $Source) {
    if (-not [IO.File]::Exists($manifestPath)) { throw 'Release manifest unavailable. Use -Source for development; a compatible verified release is required for distribution.' }
    $manifestBytes = [IO.File]::ReadAllBytes($manifestPath)
    $manifest = Read-ReleaseManifest $manifestPath $manifestBytes
}
# Plan must not compile helpers, create directories, download, or execute prerequisites.
if ($Plan) {
    Write-Output "platform=Windows-x64`nmode=$mode`nroot=$Root`nhome=$homeDirectory`ntarget=$Target`npublish_aliases=$PublishAliases"
    foreach ($name in @('uv','mise','python')) { Write-Output "$name=$($pins."${name}_version") $($pins."${name}_url") sha256=$($pins."${name}_sha256")" }
    Write-Output 'Native local NTFS; selected core/Python only. PATH is process-local; persistent PowerShell activation is a separate preview/apply operation. No machine PATH, policy, or credentials are changed.'
    return
}
Initialize-NativeStorage
$guards = [Collections.Generic.List[IDisposable]]::new()
$readers = [Collections.Generic.List[IDisposable]]::new()
$stagePath = $null
try {
    $rootGuard = [AiDlc.Bootstrap.DirectoryGuard]::new($Root, $false, $false); $guards.Add($rootGuard)
    $homeGuard = [AiDlc.Bootstrap.DirectoryGuard]::new($homeDirectory, $true, $true); $guards.Add($homeGuard)
    $binPath = Join-Path $homeDirectory 'bin'
    $bin = [AiDlc.Bootstrap.DirectoryGuard]::new($binPath, $true, $true); $guards.Add($bin)
    $downloads = [AiDlc.Bootstrap.DirectoryGuard]::new((Join-Path $homeDirectory 'downloads'), $true, $true); $guards.Add($downloads)
    $stagePath = Join-Path $binPath ('.install-' + [Guid]::NewGuid().ToString('N'))
    $stage = [AiDlc.Bootstrap.DirectoryGuard]::new($stagePath, $true, $true); $guards.Add($stage)
    $uvBytes = Get-VerifiedArtifact $downloads "uv-$($pins.uv_version)-windows-x64.zip" $pins.uv_url $pins.uv_sha256
    $toolDigests = Expand-UvArchive $uvBytes $stage
    $miseBytes = Get-VerifiedArtifact $downloads "mise-$($pins.mise_version)-windows-x64.exe" $pins.mise_url $pins.mise_sha256
    Assert-X64Executable $miseBytes
    $stage.WriteNew('mise.exe', $miseBytes)
    $toolDigests['mise.exe'] = $pins.mise_sha256
    foreach ($name in @('uv.exe','uvx.exe','mise.exe')) {
        $readers.Add($stage.OpenRead($name))
        if ((Get-BytesHash ($stage.Read($name))) -cne $toolDigests[$name]) { throw 'Staged executable changed before execution.' }
    }
    $uv = Join-Path $stagePath 'uv.exe'
    Invoke-NativeTool $uv @('--version')
    Invoke-NativeTool (Join-Path $stagePath 'mise.exe') @('--version')
    $env:PATH = "$stagePath;$($env:PATH)"
    $env:AI_DLC_BOOTSTRAP_HOME = $homeDirectory
    # Control integrity and interpreter selection, rather than inheriting external metadata.
    Remove-Item Env:UV_PYTHON_DOWNLOADS_JSON_URL -ErrorAction SilentlyContinue
    Remove-Item Env:UV_PYTHON_INSTALL_MIRROR -ErrorAction SilentlyContinue
    Remove-Item Env:UV_PYTHON -ErrorAction SilentlyContinue
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $homeDirectory 'python'
    $env:UV_PYTHON_BIN_DIR = $binPath
    $pythonGuard = [AiDlc.Bootstrap.DirectoryGuard]::new($env:UV_PYTHON_INSTALL_DIR, $true, $true); $guards.Add($pythonGuard)
    Invoke-NativeTool $uv @('--no-config','python','install','--managed-python',$pins.python_version)
    $python = (& $uv --no-config python find --managed-python $pins.python_version | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not [IO.File]::Exists($python)) { throw 'Verified managed Python is unavailable.' }
    $identity = Get-BytesHash ([Text.Encoding]::UTF8.GetBytes($Root.ToLowerInvariant()))
    $prefix = if ($Source) { 'source-' + $identity.Substring(0,16) } else { 'engine-' + $manifest.AI_DLC_ENGINE_VERSION }
    $inputHash = ''
    $reuse = $false
    $stateName = $prefix + '.json'
    if ($Source) {
        $inputText = $Root + $pins.python_version
        foreach ($path in @((Join-Path $Root 'pyproject.toml'),(Join-Path $Root 'uv.lock'))) { $inputText += Get-BytesHash ([IO.File]::ReadAllBytes($path)) }
        foreach ($path in @(Get-ChildItem -LiteralPath (Join-Path $Root 'src') -Recurse -File | Sort-Object FullName)) { if ($path.Extension -eq '.py') { $inputText += $path.FullName + (Get-BytesHash ([IO.File]::ReadAllBytes($path.FullName))) } }
        $inputHash = Get-BytesHash ([Text.Encoding]::UTF8.GetBytes($inputText))
        try {
            $prior = [Text.Encoding]::UTF8.GetString($homeGuard.Read($stateName)) | ConvertFrom-Json
            if ($prior.input_sha256 -eq $inputHash -and [IO.Path]::GetDirectoryName($prior.environment) -eq $homeDirectory -and [IO.Path]::GetFileName($prior.environment).StartsWith($prefix + '-')) {
                $candidateGuard = [AiDlc.Bootstrap.DirectoryGuard]::new($prior.environment, $false, $true)
                try {
                    $candidate = Join-Path $prior.environment 'Scripts/ai-dlc.exe'
                    $candidateScripts = [AiDlc.Bootstrap.DirectoryGuard]::new((Join-Path $prior.environment 'Scripts'), $false, $false)
                    try { $candidateHash = Get-BytesHash ($candidateScripts.Read('ai-dlc.exe')) } finally { $candidateScripts.Dispose() }
                    if ($candidateHash -eq $prior.launcher_sha256) {
                        & $candidate --version | Out-Host
                        if ($LASTEXITCODE -eq 0) { $environmentPath = $prior.environment; $reuse = $true }
                    }
                } finally { $candidateGuard.Dispose() }
            }
        } catch { Write-Verbose 'Prior source environment unavailable or unsafe; preparing an independent environment.' }
    }
    if (-not $reuse) { $environmentPath = Join-Path $homeDirectory ($prefix + '-' + [Guid]::NewGuid().ToString('N')) }
    $environmentGuard = [AiDlc.Bootstrap.DirectoryGuard]::new($environmentPath, $true, $true); $guards.Add($environmentGuard)
    if ($Source -and -not $reuse) {
        $env:UV_PROJECT_ENVIRONMENT = $environmentPath
        Invoke-NativeTool $uv @('--no-config','sync','--project',$Root,'--locked','--python',$python)
        $environmentGuard.WriteNew('ai-dlc-source-root', [Text.Encoding]::UTF8.GetBytes($Root + "`n"))
        $revision = 'unavailable (source archive)'
        if (Get-Command git.exe -ErrorAction SilentlyContinue) {
            $revision = (& git.exe -C $Root rev-parse HEAD | Out-String).Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Cannot identify source checkout revision.' }
            $dirty = (& git.exe -C $Root status --porcelain | Out-String).Trim()
            if ($dirty) { $revision += ' (dirty)' }
        }
        $environmentGuard.WriteNew('ai-dlc-source-revision', [Text.Encoding]::UTF8.GetBytes($revision + "`n"))
    } elseif (-not $Source) {
        $wheel = Get-VerifiedArtifact $downloads $manifest.AI_DLC_WHEEL_NAME $manifest.AI_DLC_WHEEL_URL $manifest.AI_DLC_WHEEL_SHA256
        $constraintsName = "constraints-$($manifest.AI_DLC_CONSTRAINTS_SHA256).txt"
        $constraints = Get-VerifiedArtifact $downloads $constraintsName $manifest.AI_DLC_CONSTRAINTS_URL $manifest.AI_DLC_CONSTRAINTS_SHA256
        $readers.Add($downloads.OpenRead($manifest.AI_DLC_WHEEL_NAME)); $readers.Add($downloads.OpenRead($constraintsName))
        Invoke-NativeTool $uv @('--no-config','venv','--allow-existing','--python',$python,$environmentPath)
        $enginePython = Join-Path $environmentPath 'Scripts/python.exe'
        Invoke-NativeTool $uv @('--no-config','pip','install','--python',$enginePython,'--require-hashes','-r',(Join-Path $downloads.PathName $constraintsName))
        Invoke-NativeTool $uv @('--no-config','pip','install','--python',$enginePython,'--no-deps',(Join-Path $downloads.PathName $manifest.AI_DLC_WHEEL_NAME))
        $environmentGuard.WriteNew('release.sh', $manifestBytes)
    }
    $enginePython = Join-Path $environmentPath 'Scripts/python.exe'
    $cli = Join-Path $environmentPath 'Scripts/ai-dlc.exe'
    Invoke-NativeTool $enginePython @('-c',"from ai_dlc.setup.commands import parse_command; from ai_dlc import _windows_storage; parse_command(dict(argv=['python','--version']))")
    Invoke-NativeTool $cli @('--version')
    $env:PATH = "$(Join-Path $environmentPath 'Scripts');$stagePath;$($env:PATH)"
    if ($Source) { $env:UV_PROJECT_ENVIRONMENT = $environmentPath }
    Invoke-NativeTool $cli @('project','setup','--root',$Root,'--target',$Target)
    # Network/setup are complete. Serialize only publication; retain all previous executable bytes on sharing refusal.
    $publication = $homeGuard.Lock('bootstrap-publication.lock')
    try {
        foreach ($name in @('uv.exe','uvx.exe','mise.exe')) {
            $bytes = $stage.Read($name)
            $existing = $null
            try { $existing = $bin.Read($name) } catch {
                $failure = $_.Exception
                while ($failure.InnerException) { $failure = $failure.InnerException }
                if ($failure -isnot [ComponentModel.Win32Exception] -or $failure.NativeErrorCode -notin @(2,3)) { throw }
            }
            if ($null -ne $existing -and (Get-BytesHash $existing) -cne (Get-BytesHash $bytes)) { throw "Existing $name differs from the reviewed pin; preserve it and inspect before replacing." }
            if ($null -eq $existing) {
                $temporary = '.publish-' + [Guid]::NewGuid().ToString('N')
                $bin.WriteNew($temporary, $bytes)
                $bin.Publish($temporary, $bin, $name, $false)
            }
        }
        $arguments = @((Join-Path $PSScriptRoot '../bootstrap/windows-select.py'),'--home',$homeDirectory,'--environment',$environmentPath,'--mode',$mode)
        if ($PublishAliases) { $arguments += '--publish' }
        if ($Source) {
            $sourceState = @{ schema=1; input_sha256=$inputHash; environment=$environmentPath; launcher_sha256=(Get-BytesHash ([IO.File]::ReadAllBytes($cli))) } | ConvertTo-Json
            $sourceStage = '.source-state-' + [Guid]::NewGuid().ToString('N')
            $homeGuard.WriteNew($sourceStage, [Text.Encoding]::UTF8.GetBytes($sourceState))
            $homeGuard.Publish($sourceStage, $homeGuard, $stateName, $true)
        }
        Invoke-NativeTool $enginePython $arguments
    } finally { $publication.Dispose() }
    $env:PATH = "$(Join-Path $environmentPath 'Scripts');$binPath;$($env:PATH)"
    if ($env:GITHUB_PATH) { [IO.File]::AppendAllText($env:GITHUB_PATH, "$(Join-Path $environmentPath 'Scripts')`n$binPath`n", [Text.UTF8Encoding]::new($false)) }
    Write-Output "Ready. Direct executable: $cli`nPrepared environment: $environmentPath`nSelected provenance: $binPath\ai-dlc-selection.json"
} catch {
    Write-Error "Native bootstrap failed; previous CLI selection is preserved. Inspect retained stage/environment paths before retry. $($_.Exception.Message)"
    throw
} finally {
    for ($i=$readers.Count-1; $i -ge 0; $i--) { $readers[$i].Dispose() }
    for ($i=$guards.Count-1; $i -ge 0; $i--) { $guards[$i].Dispose() }
    if ($stagePath) { Write-Output "Bootstrap retained $stagePath; inspect before removal." }
}
