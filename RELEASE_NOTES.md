# Release Cleanup Notes

This repo was cleaned up for public release from a working copy that still had
live operational data in it. This file is for the repo owner, not for the
public README - delete it (or move its contents into your own private notes)
once you've acted on the items below.

## 🔴 Do this before you publish, not after

None of this could be rotated from inside the cleanup itself - these are
real credentials/keys that were committed in the working copy:

- **Rotate/regenerate the `keys/id_terraform` SSH keypair.** The old one is
  burned - delete it from any AWS key pairs and generate a fresh one.
- **Regenerate your OpenVPN PKI** (CA, server, and all client certs/keys).
  The old `.ovpn` files embedded live certs and keys for ~15+ client configs
  across old deployments.
- **Change the AWS-side state:** the old copy referenced a real AWS account
  ID and ~20 real resource IDs (instances, VPC, subnets, security groups).
  If any of that infra is still running, it was built with the
  now-superseded credentials/keys above - rebuild it after rotating.
- **Treat every password that used to be hardcoded as burned**, even the
  ones that are now `CHANGEME_*` placeholders in the public files:
  `Green@Bean2Goblin#` (lab-admin/Administrator), `FlopperCatMemes5#`
  (domain-administrator), and the per-user lab passwords in
  `User-Creator.yml` (LocalAdminInst, HaroldHolt, GoughWhitlam,
  fileshare-admin, dc-syncer, lab-backdoor). Pick new ones before your next
  real deployment - don't just rename the placeholder back to the old value.
- **The `ubuntu`/`kali` box login password hashes** in `ELK-Server.yml` /
  `Kali-Server.yml` are now placeholder strings, not valid hashes. Generate
  your own with `openssl passwd -6` (or `mkpasswd -m sha-512`) before
  deploying - the playbooks will fail to actually set a usable password
  until you do.

## What changed

**Removed entirely:** the real SSH private key, every live `.ovpn` file and
the ~15 nested Ansible-`fetch` directories full of real per-deployment VPN
certs/keys, all `*.tfstate*` files (which carried your real AWS account ID
and ~100 real instance/VPC/SG IDs across old runs), and the TLS
cert/keystore files (`http.p12`, `elasticsearch-ca.pem` x2).

**Correction:** `ftp-admin-creds-DO-NOT-SHARE.txt` was initially deleted by
mistake during the first pass - it was flagged purely off the filename
pattern without checking whether it was actually referenced anywhere. It's
planted lab content, not an operational secret: `cheatsheet.txt` /
`checklist-2.txt` walk through finding it on an SMB share and using it to
pivot in as `fileshare-admin`, the same CTF-style discovery mechanism as the
Harold Holt / dc-syncer / lab-backdoor accounts. It's been restored (in both
`ansible/files/` and `refresher/files/`) with its password swapped to the
same `CHANGEME_FILESHAREADMIN_PASSWORD` placeholder already used in
`User-Creator.yml`, so it stays in sync if you change that password.
Nothing in this repo actually *provisions* the file onto a share, though -
it just sits in `files/` as a reference asset, so you'll need to place it
on the fileshare box yourself as part of setting up the scenario.

**Replaced with placeholders:** every hardcoded password across
`deployer.py`, the Packer config/bootstrap script, and all the domain/infra
playbooks (listed above). `vars.tf`'s `MANAGEMENT_IPS` (your real home/office
IPs) now defaults to an obvious placeholder with no working default - you
must set your own before `terraform apply` will produce a usable security
group. `SSM_S3_BUCKET` similarly.

**Moved, not deleted:** `commands.txt` - the repo root had a fully solved
walkthrough of the lab's intended attack chain (local admin -> Harold Holt ->
ADCS ESC1 -> domain admin via Rubeus pass-the-ticket), including a real NTLM
hash from an actual run. This spoils the exercise for anyone browsing the
source before attempting the lab, so it's now at
`docs/SOLUTIONS-SPOILERS.md` with a clear banner.
**Decide what you want here** - keep it as an instructor's answer key, or
delete it outright if you don't want the solution published at all.

**Structural cleanup** (full detail in the three agent reports under
`/tmp/claude-0/audit/agent-reports/` on the machine that built this, or just
read the current repo - the changes are all visible):
- Documented why `ansible/`, `fixer/`, and `refresher/` exist as three
  separate trees, and which one `deployer.py` actually calls for each phase
  (notably: `refresher/` is currently dead code - `deployer.py`'s
  `refresher()` points at `ansible/` instead).
- Deleted stray files (`cheatsheet.txt.bak` x2, empty `Logging.yml` x2, an
  unrelated/unreferenced PowerShell tutorial snippet that had nothing to do
  with this lab).
- Trimmed `ansible/config/requirements.txt` from a 25-package grab-bag down
  to the 2 packages actually used.
- Converted the committed offensive-tool binaries (Certify, Rubeus,
  PowerUp.ps1, winPEASx64.exe, mimikatz) into download-at-provision-time
  tasks pointed at pinned upstream releases, instead of committing the
  binaries. Two (`SetACL.exe`, `hfs.exe`) stayed committed - no credible
  stable direct-download URL exists for either, noted in-line.
  `disable-defender.exe` was removed outright - it was fully redundant with
  a `Set-MpPreference` task that already existed right next to it.
- Fixed the region inconsistency (README said one region, code hardcoded
  another in four places) into a single `aws_region` variable / `AWS_REGION`
  env var.
- Rewrote `.gitignore` to actually cover every category of file that had to
  be manually purged above, so a future real deployment can't silently
  re-leak the same things.
- Added `terraform.tfvars.example`, a `LICENSE` (MIT - placeholder copyright
  line, swap in your own name/handle if you want it), a security/legal
  disclaimer banner at the top of the README, and a "Known Limitations"
  section covering the already-acknowledged rough edges (flaky instance-wait
  logic, no error handling yet).

## What's still a placeholder / won't actually run as-is

Per your original ask, this doesn't need to fully work - it needs to be
public-ready. The things that will need real values before a deployment
actually succeeds:

- Every `CHANGEME_*` password placeholder (see the rotate list above).
- `MANAGEMENT_IPS` and `SSM_S3_BUCKET` in `vars.tf` / `terraform.tfvars`.
- A fresh `keys/id_terraform` keypair (file no longer exists at all).
- The `ubuntu`/`kali` password hashes.
- `SetACL.exe` and `hfs.exe` - the playbooks that use them still expect a
  local file in `files/`, since there was nowhere credible to point a
  download at. Either supply your own copy before deploying, or patch those
  tasks out if you don't need them.

## Final verification performed

Full secret-scan re-run against the cleaned tree, zero hits on: private
keys, certs/keystores, `.tfstate` files, IP-named leaked directories, the
real AWS account ID, the real management IPs, the old plaintext/hashed
passwords, and the personal username that was embedded in the old SSH
pubkey comment. All 51 YAML playbooks parse cleanly. File count went from
457 to 136 (secrets, duplicate binaries across three trees, and stray files
removed).
