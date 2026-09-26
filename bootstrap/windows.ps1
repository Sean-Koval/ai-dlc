# Shared native bootstrap helpers. Importing this file performs no installation.
Set-StrictMode -Version Latest
$script:NativeBootstrapDirectory = $PSScriptRoot
function Initialize-NativeStorage {
    if (-not ('AiDlc.Bootstrap.DirectoryGuard' -as [type])) {
        Add-Type -Path (Join-Path $script:NativeBootstrapDirectory 'windows-native.cs')
    }
}
function Get-BytesHash([byte[]] $Bytes) {
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $hash.Dispose() }
}
function Assert-HttpsUrl([string] $Url) {
    $uri = $null
    if (-not [Uri]::TryCreate($Url, [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -ne 'https' -or -not $uri.Host -or $uri.UserInfo -or $uri.Fragment -or $Url -notmatch '^[A-Za-z0-9:/._~%+?=&-]+$') {
        throw 'Bootstrap downloads require an explicit HTTPS URL without credentials.'
    }
}
function Read-ReleaseManifest([string] $Path, [byte[]] $Bytes = $null) {
    $keys = @('AI_DLC_ENGINE_VERSION','AI_DLC_WHEEL_NAME','AI_DLC_WHEEL_URL','AI_DLC_WHEEL_SHA256','AI_DLC_CONSTRAINTS_URL','AI_DLC_CONSTRAINTS_SHA256')
    $values = @{}
    if ($null -eq $Bytes) { $Bytes = [IO.File]::ReadAllBytes($Path) }
    $content = [Text.UTF8Encoding]::new($false, $true).GetString($Bytes)
    foreach ($line in ($content -split "`r?`n")) {
        if ($line -match '^\s*(#.*)?$') { continue }
        if ($line -notmatch '^([A-Z0-9_]+)=([A-Za-z0-9:/._~%+-]+)$') { throw 'Malformed or executable release manifest content.' }
        $key, $value = $Matches[1], $Matches[2]
        if ($keys -notcontains $key -or $values.ContainsKey($key)) { throw 'Unknown or duplicate release manifest key.' }
        $values[$key] = $value
    }
    if ($values.Count -ne $keys.Count) { throw 'Release manifest is incomplete.' }
    if ($values.AI_DLC_ENGINE_VERSION -notmatch '^\d+(\.\d+)*(?:(?:a|b|rc)\d+)?$') { throw 'Invalid engine version.' }
    if ($values.AI_DLC_WHEEL_NAME -cne "ai_dlc-$($values.AI_DLC_ENGINE_VERSION)-py3-none-any.whl") { throw 'Wheel filename/version mismatch.' }
    foreach ($key in @('AI_DLC_WHEEL_SHA256','AI_DLC_CONSTRAINTS_SHA256')) {
        if ($values[$key] -cnotmatch '^[a-f0-9]{64}$') { throw 'Invalid release SHA256.' }
    }
    Assert-HttpsUrl $values.AI_DLC_WHEEL_URL
    Assert-HttpsUrl $values.AI_DLC_CONSTRAINTS_URL
    if ([Uri]::UnescapeDataString(([Uri]$values.AI_DLC_WHEEL_URL).Segments[-1]) -cne $values.AI_DLC_WHEEL_NAME -or ([Uri]$values.AI_DLC_CONSTRAINTS_URL).Segments[-1] -cne 'requirements.txt') { throw 'Release URL filename mismatch.' }
    return $values
}
function Get-HttpsBytes([string] $Url) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    for ($redirect = 0; $redirect -lt 10; $redirect++) {
        Assert-HttpsUrl $Url
        $request = [Net.HttpWebRequest]::Create($Url)
        $request.AllowAutoRedirect = $false
        $request.UserAgent = 'AI-DLC-pinned-bootstrap'
        $request.Timeout = 120000
        $response = $request.GetResponse()
        try {
            $status = [int]$response.StatusCode
            if ($status -ge 300 -and $status -lt 400) {
                $Url = ([Uri]::new([Uri]$Url, $response.Headers['Location'])).AbsoluteUri
                continue
            }
            if ($status -ne 200) { throw "Bootstrap HTTP status $status" }
            $memory = [IO.MemoryStream]::new()
            $stream = $response.GetResponseStream()
            try {
                $buffer = New-Object byte[] 65536
                while (($count = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                    if ($memory.Length + $count -gt 536870912) { throw 'Bootstrap artifact exceeds 512 MiB budget.' }
                    $memory.Write($buffer, 0, $count)
                }
                return ,$memory.ToArray()
            } finally { $stream.Dispose(); $memory.Dispose() }
        } finally { $response.Dispose() }
    }
    throw 'Too many HTTPS redirects.'
}
function Get-VerifiedArtifact($Directory, [string] $Name, [string] $Url, [string] $Sha256) {
    Assert-HttpsUrl $Url
    if ($Sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Invalid artifact SHA256.' }
    $bytes = $null
    try { $bytes = $Directory.Read($Name) }
    catch {
        $errorObject = $_.Exception
        while ($errorObject.InnerException) { $errorObject = $errorObject.InnerException }
        if ($errorObject -isnot [ComponentModel.Win32Exception] -or $errorObject.NativeErrorCode -notin @(2,3)) { throw }
    }
    if ($null -ne $bytes) {
        if ((Get-BytesHash $bytes) -cne $Sha256) { throw "Cached artifact digest mismatch: $($Directory.PathName)\$Name. Inspect/remove the corrupt entry, then retry." }
        return ,$bytes
    }
    $bytes = Get-HttpsBytes $Url
    if ((Get-BytesHash $bytes) -cne $Sha256) { throw 'Downloaded artifact digest mismatch; nothing executed.' }
    $stage = '.download-' + [Guid]::NewGuid().ToString('N')
    $Directory.WriteNew($stage, $bytes)
    try { $Directory.Publish($stage, $Directory, $Name, $false) }
    catch {
        # A concurrent verified download may have won. Never consume its bytes unchecked.
        if ((Get-BytesHash ($Directory.Read($Name))) -cne $Sha256) { throw }
        Write-Warning "Verified download stage retained: $($Directory.PathName)\$stage"
    }
    return ,$bytes
}
function Expand-UvArchive([byte[]] $Bytes, $Directory) {
    Add-Type -AssemblyName System.IO.Compression
    $memory = [IO.MemoryStream]::new($Bytes, $false)
    $archive = [IO.Compression.ZipArchive]::new($memory, [IO.Compression.ZipArchiveMode]::Read)
    try {
        $entries = @{}
        $digests = @{}
        foreach ($entry in $archive.Entries) {
            $name = $entry.FullName
            if ($name -match '(^[/\\]|[\\:]|(^|/)\.\.?(?:/|$)|[. ](?:/|$))' -or (($entry.ExternalAttributes -shr 16) -band 0xF000) -eq 0xA000) { throw 'Unsafe archive entry; extraction refused.' }
            if ($entry.Length -gt 268435456) { throw 'Archive entry exceeds size budget.' }
            if ($entries.ContainsKey($name.ToLowerInvariant())) { throw 'Duplicate archive entry.' }
            $entries[$name.ToLowerInvariant()] = $entry
        }
        foreach ($tool in @('uv.exe','uvx.exe')) {
            $found = @($archive.Entries | Where-Object { $_.Name -ceq $tool })
            if ($found.Count -ne 1) { throw "Archive must contain exactly one $tool." }
            $inputStream = $found[0].Open(); $outputStream = [IO.MemoryStream]::new()
            try { $inputStream.CopyTo($outputStream); $payload = $outputStream.ToArray() }
            finally { $inputStream.Dispose(); $outputStream.Dispose() }
            Assert-X64Executable $payload
            $Directory.WriteNew($tool, $payload)
            $digests[$tool] = Get-BytesHash $payload
        }
        return $digests
    } finally { $archive.Dispose(); $memory.Dispose() }
}
function Assert-X64Executable([byte[]] $Bytes) {
    if ($Bytes.Length -lt 64 -or $Bytes[0] -ne 77 -or $Bytes[1] -ne 90) { throw 'Artifact is not a Windows executable.' }
    $offset = [BitConverter]::ToInt32($Bytes, 60)
    if ($offset -lt 64 -or $offset -gt $Bytes.Length - 6 -or [BitConverter]::ToUInt32($Bytes, $offset) -ne 0x4550 -or [BitConverter]::ToUInt16($Bytes, $offset + 4) -ne 0x8664) { throw 'Artifact is not a Windows x64 executable.' }
}
function Invoke-NativeTool([string] $Executable, [string[]] $Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Native command failed ($LASTEXITCODE): $Executable" }
}
function Assert-NativeLocation([string] $Path, [bool] $MustExist = $false) {
    if ($Path -notmatch '^[A-Za-z]:[\\/]' -or $Path -match '^[\\/]{2}') { throw 'Bootstrap requires an absolute local NTFS path; UNC, device and drive-relative paths are unsupported.' }
    $absolute = [IO.Path]::GetFullPath($Path)
    $rootPath = [IO.Path]::GetPathRoot($absolute)
    $drive = [IO.DriveInfo]::new($rootPath)
    if ($drive.DriveType -ne [IO.DriveType]::Fixed -or $drive.DriveFormat -ne 'NTFS') { throw 'Bootstrap requires a local fixed NTFS drive.' }
    $current = $rootPath
    foreach ($part in $absolute.Substring($rootPath.Length).Split([char]'\')) {
        if (-not $part) { continue }
        $current = Join-Path $current $part
        try { $attributes = [IO.File]::GetAttributes($current) }
        catch [IO.FileNotFoundException] { if ($MustExist) { throw }; break }
        catch [IO.DirectoryNotFoundException] { if ($MustExist) { throw }; break }
        if (($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or ($attributes -band [IO.FileAttributes]::Directory) -eq 0) { throw "Unsafe bootstrap location (reparse point or non-directory): $current" }
    }
}
function Open-VerifiedArtifact($Directory, [string] $Name, [string] $Sha256) {
    $reader = $Directory.OpenRead($Name)
    try {
        if ((Get-BytesHash ($Directory.Read($Name))) -cne $Sha256) { throw 'Artifact digest changed before consumption.' }
        return $reader
    } catch { $reader.Dispose(); throw }
}
function Open-ManagedPython([string] $InstallDirectory, [string] $Version) {
    # uv 0.9.11 managed.rs: exact patch directory, never the optional minor-version junction.
    $directory = Join-Path $InstallDirectory "cpython-$Version-windows-x86_64-none"
    $guard = $null
    try { $guard = [AiDlc.Bootstrap.DirectoryGuard]::new($directory, $false, $true) }
    catch {
        $failure = $_.Exception
        while ($failure.InnerException) { $failure = $failure.InnerException }
        if ($failure -is [ComponentModel.Win32Exception] -and $failure.NativeErrorCode -in @(2,3)) { return $null }
        throw
    }
    try {
        $reader = $guard.OpenRead('python.exe')
        try {
            Assert-X64Executable ($guard.Read('python.exe'))
            return @{ Guard=$guard; Reader=$reader; Executable=(Join-Path $directory 'python.exe') }
        } catch { $reader.Dispose(); throw }
    } catch { $guard.Dispose(); throw }
}
function Get-SourceProvenance([string] $Root) {
    if (-not (Test-Path -LiteralPath (Join-Path $Root '.git')) -or -not (Get-Command git.exe -ErrorAction SilentlyContinue)) { return 'unavailable (source archive)' }
    $revision = (& git.exe -C $Root rev-parse HEAD | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot identify source checkout revision.' }
    $dirty = (& git.exe -C $Root status --porcelain | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect source checkout status.' }
    if ($dirty) {
        $difference = (& git.exe -C $Root diff --binary HEAD | Out-String)
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect source checkout changes.' }
        $revision += ' (dirty:' + (Get-BytesHash ([Text.Encoding]::UTF8.GetBytes($dirty + $difference))) + ')'
    }
    return $revision
}
