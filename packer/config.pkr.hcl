packer {
  required_plugins {
    amazon = {
      version = ">= 0.0.1"
      source = "github.com/hashicorp/amazon"
    }
  }
}

variable "region" {
  type    = string
  default = "us-west-2"
}

locals { timestamp = regex_replace(timestamp(), "[- TZ:]", "") }

# source blocks are generated from your builders; a source can be referenced in
# build blocks. A build block runs provisioner and post-processors on a
# source.
source "amazon-ebs" "firstrun-windows" {
  ami_name      = "packer-windows-demo-${local.timestamp}"
  communicator  = "winrm"
  instance_type = "t2.micro"
  region        = "${var.region}"
  source_ami_filter {
    filters = {
      name                = "Windows_Server-2019-English-Full*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    most_recent = true
    owners      = ["amazon"]
  }
  user_data_file = "packer/bootstrap_win.txt"
  winrm_password = "CHANGEME_LAB_ADMIN_PASSWORD"
  winrm_username = "Administrator"
}

build {
  name    = "learn-packer"
  sources = ["source.amazon-ebs.firstrun-windows"]
  provisioner "powershell" {
    inline = [
      "C:\\ProgramData\\Amazon\\EC2-Windows\\Launch\\Scripts\\InitializeInstance.ps1 -Schedule",
      "C:\\ProgramData\\Amazon\\EC2-Windows\\Launch\\Scripts\\SysprepInstance.ps1 -NoShutdown",
      "net user lab-admin CHANGEME_LAB_ADMIN_PASSWORD /add /Y",
      "net localgroup administrators lab-admin /add"
#      "wmic useraccount where \"name='Administrator'\" set PasswordExpires=FALSE"
    ]
  }
}
