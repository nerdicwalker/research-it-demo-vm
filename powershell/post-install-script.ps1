# post-install-script
# version 0.1.0
[CmdletBinding()]
Param
(
    [String] $azureKeyVaultName,
    [String] $azureKeyVaultSecret
)

$LOGFILE = "c:\installation-sources\logs\post-install-script.log"
$INSTALLDIR = "c:\installation-sources"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Function Write-Log([String] $logText) {
    '{0:u}: {1}' -f (Get-Date), $logText | Out-File $LOGFILE -Append
}

Function Install-Software([String] $appName, [String] $urlToInstallerFile, [String] $installerFile, [String] $installArguments) {
    Write-Log "Installing $appName."
    $installPath = "$INSTALLDIR\$appName"
    Write-Log "Creating $installPath directory."
    New-Item -ItemType Directory -Path $installPath
    Write-Log "Directory $installPath created."
    $client = New-Object System.Net.WebClient
    Write-Log "Downloading $urlToInstallerFile and saving it as $installerFile."
    $client.DownloadFile($urlToInstallerFile, "$installPath\$installerFile")
    Write-Log "$installerFile was downloaded in the $installPath directory."
    Write-Log "Installing $appName."
    $installerCommand = "$installPath\$installerFile $installArguments"
    Invoke-Expression -Command $InstallerCommand
    Write-Log "$appName installed."
}

Function Main {
    try {
        New-Item -ItemType Directory -Path c:\installation-sources\logs
        Write-Log "Log directory created."
        New-Item -ItemType Directory -Path c:\installation-sources\scripts
        Write-Log "Scripts directory created."
    }
    catch {
        Throw $_
    }
    cp windows\init-and-format-data-disk.ps1 c:\installation-sources\scripts\init-and-format-data-disk.ps1
    cp windows\install-jumpcloud-agent.ps1 c:\installation-sources\scripts\install-jumpcloud-agent.ps1
    Write-Log "Starting Audiosrv service.." 
    Start-Service -Name Audiosrv
    Set-Service -Name Audiosrv -StartupType Automatic
}

try {
    Main    
}
catch {
    Write-Log "$_"
    Throw $_   
}