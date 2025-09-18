# This script checks for the presence of Visual Studio Build Tools 2022 and installs it if it is not found.

#region Configuration
param (
    [string]$InstallLocation
)

# Define the installation path. If no path is provided, use a default.
# The default path for VS Build Tools 2022 is typically in the Program Files (x86) directory.
$defaultInstallPath = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
if ([string]::IsNullOrWhiteSpace($InstallLocation)) {
    $installPath = $defaultInstallPath
    Write-Host "No installation path specified. Using default path: $installPath" -ForegroundColor Yellow
} else {
    $installPath = $InstallLocation
    Write-Host "Using specified installation path: $installPath" -ForegroundColor Green
}

# Define the installer download URL
$installerUrl = "https://aka.ms/vs/17/release/vs_BuildTools.exe"

# Define the workloads and components to install
# These are the common ones for C++ and .NET development.
# You can find a full list of workload and component IDs on the Microsoft Learn website.
$workloads = @(
    "Microsoft.VisualStudio.Workload.VCTools"
    "Microsoft.VisualStudio.Workload.ManagedDesktopBuildTools"
)
$components = @(
    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64"
)
#endregion

#region Helper Functions
function Test-VsBuildToolsInstallation {
    <#
    .SYNOPSIS
    Tests if Visual Studio Build Tools 2022 is installed.
    .DESCRIPTION
    This function checks for the presence of the Visual Studio Build Tools 2022 installation
    by using the 'vswhere.exe' utility, which is the recommended way to find Visual Studio instances.
    #>
    Write-Host "Checking for Visual Studio Build Tools 2022 installation..."

    # Check for the location of vswhere.exe
    $vswherePath = "$env:ProgramFiles(x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vswherePath)) {
        Write-Warning "vswhere.exe not found. This might indicate that the Visual Studio Installer is not present."
        return $false
    }

    # Use vswhere to search for Build Tools 2022
    $vsInstance = & "$vswherePath" -products Microsoft.VisualStudio.Product.BuildTools `
                                 -version 17.0 `
                                 -format json

    if ($vsInstance -and ($vsInstance | ConvertFrom-Json).Count -gt 0) {
        Write-Host "Visual Studio Build Tools 2022 is already installed." -ForegroundColor Green
        return $true
    } else {
        Write-Host "Visual Studio Build Tools 2022 not found." -ForegroundColor Yellow
        return $false
    }
}
#endregion

#region Main Script Logic
if (-not (Test-VsBuildToolsInstallation)) {
    Write-Host "Starting installation process..."

    # Define the installer arguments for a silent install with no prompts
    $arguments = "--quiet --wait --norestart --installPath `"$installPath`""

    # Add workloads and components to the arguments
    foreach ($workload in $workloads) {
        $arguments += " --add $workload"
    }
    foreach ($component in $components) {
        $arguments += " --add $component"
    }

    # Define the temporary path for the installer
    $tempInstallerPath = Join-Path $env:TEMP "vs_BuildTools.exe"

    # Download the installer
    Write-Host "Downloading Visual Studio Build Tools 2022 installer from $installerUrl..."
    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $tempInstallerPath -UseBasicParsing
        Write-Host "Download complete." -ForegroundColor Green
    }
    catch {
        Write-Error "Failed to download the installer. Please check your internet connection and try again."
        exit 1
    }

    # Start the installation process
    Write-Host "Running installer with arguments: $arguments"
    try {
        $process = Start-Process -FilePath $tempInstallerPath -ArgumentList $arguments -PassThru -Wait
        if ($process.ExitCode -eq 0) {
            Write-Host "Visual Studio Build Tools 2022 installed successfully." -ForegroundColor Green
        }
        else {
            Write-Error "Installation failed with exit code $($process.ExitCode)."
        }
    }
    catch {
        Write-Error "An error occurred during installation: $_"
        exit 1
    }
}

Write-Host "Script execution completed."
#endregion
