<#
.SYNOPSIS
    Installs and configures the gcp-log-transformer Python script as a Windows service using NSSM.

.DESCRIPTION
    This script automates the setup of the gcp-log-transformer service. It performs the following actions:
    - Ensures it is run with Administrator privileges.
    - Checks for and installs dependencies: Chocolatey, Python, and NSSM.
    - Sets up the necessary project directories and log files.
    - Installs Python package requirements from the project directory.
    - Removes any pre-existing instance of the service for a clean installation.
    - Installs, configures, and starts the service using NSSM.
    - Displays a summary of the installation and lists all NSSM-managed services.

.NOTES
    Author: syedanees816@gmail.com
    Version: 1.0
    Last Updated: 2025-10-13
#>

#Requires -RunAsAdministrator

[CmdletBinding(SupportsShouldProcess = $true)]
param()

$serviceName = "gcp-log-transformer"

$projectDir = (Split-Path -Parent $PSScriptRoot)
$logTransformerScript = Join-Path -Path $projectDir -ChildPath "src\main.py"
$nssmLogDir = Join-Path -Path $projectDir -ChildPath "nssm-logs"
$logFile = Join-Path -Path $nssmLogDir -ChildPath "service.log"

function Install-Chocolatey {
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host "Chocolatey not found. Installing..." -ForegroundColor Yellow
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        $installScript = (New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1')
        Invoke-Expression $installScript
    }
    else {
        Write-Host "Chocolatey is already installed." -ForegroundColor Green
    }
}

function Install-ChocoPackage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageName,

        [Parameter(Mandatory = $true)]
        [string]$CommandName
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        Write-Host "Installing $PackageName via Chocolatey..." -ForegroundColor Yellow
        choco install $PackageName -y --force
    }
    else {
        Write-Host "$PackageName is already installed." -ForegroundColor Green
    }
}

function Write-Header {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )
    $line = "=" * 60
    Write-Host "`n$line" -ForegroundColor Magenta
    Write-Host (" " * ((60 - $Title.Length) / 2)) + $Title -ForegroundColor Magenta
    Write-Host "$line" -ForegroundColor Magenta
}

Write-Host "Success: Running with Administrator privileges." -ForegroundColor Green

Write-Header "Step 1: Checking Dependencies"
Install-Chocolatey
Install-ChocoPackage -PackageName "python" -CommandName "python"
Install-ChocoPackage -PackageName "nssm" -CommandName "nssm"

try {
    $pythonExePath = (Get-Command python).Source
    $pipExePath = (Get-Command pip).Source
}
catch {
    Write-Error "Could not find Python or Pip executable. Please ensure Python is installed and in your PATH."
    exit 1
}

Write-Header "Step 2: Setting up Project Environment"
Set-Location -Path $projectDir

if (-not (Test-Path -Path $nssmLogDir)) {
    Write-Host "Creating log directory: $nssmLogDir"
    New-Item -ItemType Directory -Path $nssmLogDir -Force | Out-Null
}

Write-Host "Installing Python requirements from '$projectDir'..."
& $pipExePath install . --quiet --no-warn-script-location


Write-Header "Step 3: Installing the Windows Service"
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Warning "Service '$serviceName' already exists. Re-installing..."
    if ($existingService.Status -ne 'Stopped') {
        Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    }
    nssm remove $serviceName confirm
}

Write-Host "Installing service '$serviceName'..."
nssm install $serviceName "$pythonExePath"
nssm set $serviceName AppParameters $logTransformerScript
nssm set $serviceName AppDirectory $projectDir
nssm set $serviceName AppStderr $logFile
nssm set $serviceName AppStdout $logFile

Write-Host "`nVerifying service configuration..." -ForegroundColor Cyan
Write-Host "Application: $(nssm get $serviceName Application)"
Write-Host "AppDirectory: $(nssm get $serviceName AppDirectory)"
Write-Host "AppParameters: $(nssm get $serviceName AppParameters)"

Write-Host "Starting service '$serviceName'..."
nssm start $serviceName


Write-Header "Setup Complete!"
Write-Host "Service Name: $serviceName"
Write-Host "Project Path: $projectDir"
Write-Host "Log File:     $logFile"
Write-Host "`nYou can manage the service with the following commands:"
Write-Host " - Status:   Get-Service $serviceName"
Write-Host " - Stop:     Stop-Service $serviceName"
Write-Host " - Start:    Start-Service $serviceName"
Write-Host " - Restart:  Restart-Service $serviceName"

Write-Header "All NSSM Services on this Machine"

Get-CimInstance Win32_Service |
    Where-Object { $_.PathName -like '*nssm.exe*' } |
    Select-Object Name, DisplayName, State, StartMode, ProcessId |
    Format-Table -AutoSize

Pause
