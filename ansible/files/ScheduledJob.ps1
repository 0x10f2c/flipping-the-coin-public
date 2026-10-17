$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration ([System.TimeSpan]::MaxValue)
$path = "C:/UserSignIn.ps1"
Register-ScheduledJob -Name "UpdateVersion" -FilePath $path -Trigger $trigger