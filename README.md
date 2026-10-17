> **Security & Legal Notice:** This repo stands up an intentionally vulnerable Active Directory environment preloaded with known offensive-security tooling (Rubeus, Certify, mimikatz, etc.). It is for authorized training and educational use only. Deploy it only into cloud accounts and networks you own or are explicitly authorized to test in. The maintainers and contributors are not responsible for any misuse of this lab or the tools it provisions.

# FlippingTheCoin
Defcon31 Training labs for workshops and detection

This repo is a package of multiple cloud tools that enable the upbring of an active directory lab for training purposes.

The current tech stack is as follows:
- Packer, used to create a custom amazon AMI that has winrm enabled
- Terraform, used for cloud deployment of boxes and enviornment
- Ansible, used for configuration of any boxes (Over ssh for linux, over winrm for windows)
- Python deployer script that ties this all together and scales the infrastructure


---
## Repo Layout

There are three near-identical Ansible trees - `ansible/`, `fixer/` and `refresher/` - one per build phase that `deployer.py` can run. They started as copies of each other for each phase and have since drifted slightly; they are not auto-generated from a single source, so changes to one tree do not propagate to the others.

- `ansible/` - the playbooks used for the **first run** (`deployer.py -f`), scaling/imaging, `--deploy`, and `--redeployer`. In practice `deployer.py`'s `refresher()` function also calls into this tree rather than `refresher/`, so `ansible/` is the tree actually exercised for both first-run and refresh.
- `fixer/` - the playbooks used by the **fix** phase (`deployer.py --fix` / `--fixlab`), which only re-applies the VPN, ELK and Kali infra playbooks (not the domain-playbooks) to patch up a lab after scaling.
- `refresher/` - intended for the **refresh** phase, but `deployer.py`'s `refresher()` function currently points at `ansible/domain-playbooks/...` and `ansible/infra-playbooks/...`, not at this tree. `refresher/` is effectively unused by the current `deployer.py` and kept here mainly as the historical basis the `ansible/` tree was refreshed from; treat it as reference material rather than live code.

---
## Offensive Tool Binaries

The domain-playbooks intentionally install real offensive-security tooling
(Rubeus, Certify, mimikatz, winPEAS, PowerUp, etc.) onto the lab boxes so
students can practice with them. For the public release, these binaries are
no longer committed into `ansible/files/` and `refresher/files/` - instead
the relevant Ansible tasks fetch them at provision time from their pinned
upstream GitHub releases (with a specific tag/commit noted in a comment next
to each download task) using `win_get_url`. This is standard practice for
public red-team-lab repos because committing raw `.exe`/`.ps1` offensive
tools directly into a public git history routinely trips GitHub's
secret/malware scanning and some AV vendors on clone/checkout, bloats the
repository, and makes it harder to track which exact tool version is in use.
A couple of binaries (`SetACL.exe`, `hfs.exe`) have no credible, stable,
directly-downloadable upstream URL and are still kept as committed files;
those tasks carry a comment explaining why.

---
## Important Note

The AWS region is now a single configurable value instead of being hardcoded in several places: `vars.tf` defines `variable "aws_region"` (default `us-west-2`), which `main.tf`'s provider block and `packer/config.pkr.hcl`'s `region` variable both reference. `deployer.py` reads the same default from the `AWS_REGION` environment variable (`os.environ.get("AWS_REGION", "us-west-2")`). To deploy to another region (e.g. `ap-southeast-2`), set `aws_region` in a `terraform.tfvars` file (see `terraform.tfvars.example`) and export `AWS_REGION` with the matching value before running `deployer.py`.

---
## Known Limitations

This is a v1 public release; the following rough edges are known and acknowledged rather than oversights:

- **Instance-ready waiting is flaky.** `deployer.py` has a standing TODO on this (`# This isnt waiting we still get the script running on not ok instances` / `# TODO: FIX THIS` above `ec2checkerstaging()`'s call site) - the script pauses and polls EC2/system status waiters, but it is not yet strictly scoped to the exact instance IDs of the current run, so Ansible can start against boxes that aren't fully ready. If a run fails here, rerun `deployer.py -f` as described in the Usage Guide below.
- **No error handling yet.** As the deployer itself prints during the ansible stage ("there is no error handling yet"), failures generally surface as raw command output rather than a clean error message - read the console output rather than relying on exit codes.
- **No region validation.** Setting `AWS_REGION` / `aws_region` to a region without the AMIs or base images this lab expects will fail at `terraform apply` or `packer build` time with provider errors, not a friendly message up front.

---
## Usage Guide

To deploy first off create the AMI image that will be the base image for the windows machine.

`python3 deployer.py -p`

Take the outputed AMI image number and replace the `ami_packer_build` variable in vars.tf before moving past this step.

After the above is done you can run the deployer through the first run iteration which will bring up the terraform and then configure it with ansible.

`python3 deployer.py -f`

Note sometimes the ansible fails or will not connect back in after a reboot, generally speaking its easiest to simply rerun the command above and hit N at the terraform prompt. The ansible will quickly rerun over what has already been configured and identify what failed and resolve those configurations.

Once this is done test the infrastructure to ensure the pathway works, if all is good then image the infrastructure using the following command.

`python3 deployer.py -i`

This will take images of the entire infrastructure that we can then scale from. At this point the lab is ready to be scaled out to a classroom.

Decide how many labs you need, keep in mind you'll want one for yourself in order to demonstrate to the class. Run the following command with your number, the example below will deploy 20 seperate labs.

`python3 deployer.py --deploy 20`

Once this is done simply fix the labs to ensure that credentials are in memory, and that things are rightly configured.

`python3 deployer.py --fix 20`

Now simply hand out the VPN files to the class.

--- 

## Tips n Tricks

### How to replace a tainted box manually
If a box becomes tainted and needs to be killed use the following terraform command

`terraform apply -replace="aws_instance.example[0]"`

This will destroy the box and bring it back up, afterwards run the relevent ansible against it. You can do this by taking the commands out of deployer.py and running them manually, or by simply letting deployer do a first run again in which case ansible will skip the other boxes and configure this new one.

If the DC is burned however, probably worth completely rerolling infrasturcture.

This is automated below.

### How to find the names of Terraform resources

To use the above replacement method you need to use the following command to identifiy the names:

`terraform state list`

### Destroy a Singular Lab Workpsace

Run the following command:

`python3 deployer.py --destroylab 1`

### Restart a Singular Lab WorkSpace

You can reboot a lab by using the following

`python3 deployer.py --restartlab 22`

This will reboot the lab22 workspace.

### Redeploy a single machine in a workspace lab

You can redeploy a single machine in a workspace using the following format.

`python3 deployer.py --redeployer <machine> <workspace>`

Make sure you are in the right workspace and then run `terraform state list` to get the machine name of what needs to be restarted.

### Redeploy a single workspace lab

First off make sure you destroy the lab you want to redeploy following the instructions above. Afterwards you can redeploy the lab fully by using the following command:

TODO

After that fix that particular lab using the following command:

`python3 deployer.py --fixlab 1`

