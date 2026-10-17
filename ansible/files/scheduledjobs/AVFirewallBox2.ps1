# Remote for User Harold Holt to Box 2

$username = 'demo.lab\HaroldHolt'
$password = 'CHANGEME_HAROLDHOLT_PASSWORD'

$secpw = ConvertTo-SecureString $password -AsPlainText -Force
$cred  = New-Object Management.Automation.PSCredential ($username, $secpw)

Invoke-Command -ComputerName Box2 -ScriptBlock { ( Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False ), (Set-MpPreference -DisableRealtimeMonitoring $false) } -Credential $cred
