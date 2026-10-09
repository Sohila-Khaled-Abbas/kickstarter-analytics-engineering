<#
.SYNOPSIS
    Power BI Desktop Git Auto-Sync & Version Control Daemon (PowerShell).
.DESCRIPTION
    Monitors the powerbi/ folder for changes made during Power BI Desktop sessions.
    Automatically stages, commits, and pushes changes to GitHub on every save.
#>

[CmdletBinding()]
param (
    [int]$DebounceSeconds = 6,
    [int]$PollIntervalSeconds = 2
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$WatchDir = Join-Path $RepoRoot "powerbi"

Write-Host "===============================================================================" -ForegroundColor Green
Write-Host "     KICKSTARTER POWER BI GIT AUTO-SYNC DAEMON (POWERSHELL)                   " -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Green
Write-Host "Watching directory : $WatchDir"
Write-Host "Debounce window    : ${DebounceSeconds}s"
Write-Host "Press Ctrl+C to terminate.`n" -ForegroundColor Yellow

function Get-LatestMTime {
    $files = Get-ChildItem -Path $WatchDir -Recurse -File -Include *.json, *.tmdl, *.pbir, *.pbism, *.pbip -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch "\.pbi\\(localSettings|editorSettings)" }
    if ($files) {
        return ($files | Measure-Object -Property LastWriteTime -Maximum).Maximum
    }
    return [datetime]::MinValue
}

$lastSynced = Get-LatestMTime
$pendingSync = $false
$lastChangeTime = [datetime]::MinValue

while ($true) {
    try {
        $currentMTime = Get-LatestMTime
        $now = Get-Date

        if ($currentMTime -gt $lastSynced) {
            $lastChangeTime = $now
            $lastSynced = $currentMTime
            $pendingSync = $true
            Write-Host -NoNewline "[WAIT] Save detected. Debouncing for ${DebounceSeconds}s to ensure write completion...`r" -ForegroundColor Yellow
        }

        if ($pendingSync -and ($now - $lastChangeTime).TotalSeconds -ge $DebounceSeconds) {
            Write-Host "`n[$($now.ToString('yyyy-MM-dd HH:mm:ss'))] Changes detected in Power BI project files." -ForegroundColor Cyan
            
            # Stage changes
            git -C $RepoRoot add .
            
            # Check diff
            git -C $RepoRoot diff --cached --quiet
            if ($LASTEXITCODE -ne 0) {
                $commitMsg = "auto(powerbi): update model and report definitions [$($now.ToString('yyyy-MM-dd HH:mm:ss'))]"
                Write-Host "  -> Committing: $commitMsg" -ForegroundColor Gray
                git -C $RepoRoot commit -m $commitMsg
                
                Write-Host "  -> Pushing to GitHub (origin main)..." -ForegroundColor Gray
                git -C $RepoRoot push origin main
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  [SUCCESS] Successfully pushed Power BI updates to GitHub!" -ForegroundColor Green
                } else {
                    Write-Host "  [WARNING] Push failed (check internet connection). Committed locally." -ForegroundColor Red
                }
            } else {
                Write-Host "  -> No net differences to commit." -ForegroundColor Gray
            }

            $pendingSync = $false
            $lastSynced = Get-LatestMTime
            Write-Host "[READY] Watching for next Power BI save event...`n" -ForegroundColor DarkGray
        }

        Start-Sleep -Seconds $PollIntervalSeconds
    }
    catch {
        Write-Host "Error: $_" -ForegroundColor Red
        Start-Sleep -Seconds 5
    }
}
