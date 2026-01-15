<#
.SYNOPSIS
    Log simulator for testing and validating the GCP log transformation.

.DESCRIPTION
    This script automates the process of random log generation at various disk locations.
    It performs the following actions:
    - Creates a root testing directory.
    - Creates 4 sub-directories each containing a service.log file.
    - Generates random log entries with different log levels and messages.
    - Continuously appends log entries to each service.log file at specified intervals.

.NOTES
    Author: syedanees816@gmail.com
    Version: 1.0
#>

param(
    [bool]$Debug = $False,
    [int]$DelayMs = 500,
    [int]$TotalRounds = 0,
    [string[]]$Services = @("alpha","beta","gamma","delta")
)

$LogLevels = @("INFO", "WARNING", "ERROR", "CRITICAL")
$Messages = @{
    "INFO"     = @("Routine check completed", "Heartbeat signal received", "Configuration loaded successfully")
    "WARNING"  = @("High memory usage detected", "Slow response time observed", "Disk space running low")
    "ERROR"    = @("Failed to connect to database", "Timeout in external API", "Unhandled exception caught")
    "CRITICAL" = @("System overload detected", "Memory corruption in progress", "Kernel panic in service thread")
}

$ProjectDir = (Resolve-Path -Path "./").ProviderPath
$examplesRoot = Join-Path $ProjectDir "testing"

function New-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DirPath,

        [Parameter(Mandatory = $true)]
        [string]$FilePath
    )

    if (-not (Test-Path -Path $DirPath)) {
            New-Item -ItemType Directory -Path $DirPath -Force | Out-Null
        }

        if (-not (Test-Path -Path $FilePath)) {
            New-Item -ItemType File -Path $FilePath -Force | Out-Null
        } else {
            Clear-Content -Path $FilePath
        }

        $fs = [System.IO.File]::Open(
            $FilePath,
            [System.IO.FileMode]::Append,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::ReadWrite
        )

        $sw = New-Object System.IO.StreamWriter($fs)
        $sw.AutoFlush = $true
        $writers[$svc] = $sw
        $fileStreams[$svc] = $fs

        Write-Host "Opened writer for service '$svc' -> $logPath"
        
}

if (-not (Test-Path -Path $examplesRoot)) {
    Write-Host "Creating examples root: $examplesRoot"
    New-Item -ItemType Directory -Path $examplesRoot -Force | Out-Null
}

$writers = @{}
$fileStreams = @{}

try {
    foreach ($svc in $Services) {
        $svcDir = Join-Path $examplesRoot ("service_$svc")
        $logPath = Join-Path $svcDir "service.log"

        New-Directory -DirPath $svcDir -FilePath $logPath
    }

    Write-Host "`nStarting log generation. Press Ctrl+C to stop.`n"

    while ($true) {
        foreach ($svc in $Services) {
            $level = Get-Random -InputObject $LogLevels
            $message = Get-Random -InputObject $Messages[$level]
            $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss,fff")

            $logLine = "[" + $timestamp + "] " + "[" + $level + "]" + ": " + $message + " in service " + $svc + "!"

            $writers[$svc].WriteLine($logLine)

            if ($Debug) {
                Write-Host "$logLine"
            }
        }
        Start-Sleep -Milliseconds $DelayMs
    }
}
catch {
    Write-Error "An error occurred: $_"
}
finally {
    Write-Host "`nClosing writers..."
    foreach ($svc in $Services) {
        try {
            if ($writers.ContainsKey($svc)) {
                $writers[$svc].Close()
            }
            if ($fileStreams.ContainsKey($svc)) {
                $fileStreams[$svc].Close()
            }
        }
        catch {
            Write-Warning "Error closing stream for $($svc): $($_)"
        }
    }
    Write-Host "All writers closed."
}
