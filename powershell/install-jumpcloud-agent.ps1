# install-jumpcloud-agent.ps1
# version 0.1.0
[CmdletBinding()]
Param
(
    [String] $azureKeyVaultName,
    [String] $azureKeyVaultSecret
)


$LOGFILE = "c:\installation-sources\logs\install-jumpcloud-agent.log"
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

Function Get-JumpCloud-Install-Key([String] $azureKeyVaultName, [String] $azureKeyVaultSecret) {
    Write-Log "Fetching secret $azureKeyVaultSecret from key vault $azureKeyVaultName."
    $MSI_ENDPOINT = "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://vault.azure.net"
    try {
        $response = Invoke-WebRequest -Uri $MSI_ENDPOINT -UseBasicParsing -Method GET -Headers @{Metadata = "true" }
        $content = $response.Content | ConvertFrom-Json
        $accessToken = $content.access_token
        $KeyVaultURL = "https://" + $azureKeyVaultName + ".vault.azure.net/secrets/" + $azureKeyVaultSecret + "?api-version=2016-10-01"
        $kvSecret = Invoke-WebRequest -Uri $KeyVaultURL -UseBasicParsing -Method GET -Headers @{Authorization = "Bearer $accessToken" }
        $kvContent = $kvSecret | ConvertFrom-Json
        $jumpCloudInstallSecret = $kvContent.value
    }
    catch {
        throw $_   
    }
    Write-Log "Found the secret $azureKeyVaultSecret in key vault $azureKeyVaultName."
    return $jumpCloudInstallSecret
}

Function Main {    
    $jumpCloudInstallSecret = Get-JumpCloud-Install-Key $azureKeyVaultName $azureKeyVaultSecret
    Install-Software "Jumpcloud" "https://s3.amazonaws.com/jumpcloud-windows-agent/production/JumpCloudInstaller.exe" "JumpCloudInstaller.exe" "-k $jumpCloudInstallSecret /VERYSILENT /NORESTART /SUPPRESSMSGBOXES"
}

try {
    Main    
}
catch {
    Write-Log "$_"
    Throw $_   
}