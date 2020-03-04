$LOGFILE = "c:\installation-sources\logs\post-install-script.log"

Function Write-Log([String] $logText) {
    '{0:u}: {1}' -f (Get-Date), $logText | Out-File $LOGFILE -Append
}

Function Format-Disks() {
    $disks = Get-Disk | Where-Object PartitionStyle -eq 'RAW' | Sort-Object Number

    $letters = 70..89 | ForEach-Object { [char]$_ }
    $count = 0
    $label = "research-data"

    ForEach ($disk in $disks) {
        Write-Log "Initializing disk $disk."
        $driveLetter = $letters[$count].ToString()
        $disk |
        Initialize-Disk -PartitionStyle MBR -PassThru |
        New-Partition -UseMaximumSize -DriveLetter $driveLetter |
        Format-Volume -FileSystem NTFS -NewFileSystemLabel $label -Confirm:$false -Force
        Write-Log "Disk $disk initialized."
        $count++
    }
}

Function Main {
    try {
        New-Item -ItemType Directory -Path c:\installation-sources\logs
        Write-Log "Log directory created."
    }
    catch {
        Throw $_
    }
    Format-Disks
}

try {
    Main    
}
catch {
    Write-Log "$_"
    Throw $_   
} 