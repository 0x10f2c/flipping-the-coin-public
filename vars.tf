#Alot ripped from xpn and expanded for our packer/ ansible needs

# Single source of truth for the AWS region. Override in terraform.tfvars
# (see terraform.tfvars.example) or with TF_VAR_aws_region instead of
# editing this file.
variable "aws_region" {
  description = "AWS region to deploy the lab into."
  type        = string
  default     = "us-west-2"
}

#Update this var for any new packer ami images
variable "ami_packer_build" {
    default = "ami-06c8844749faedcd8"  
}

variable "PATH_TO_PUBLIC_KEY" {
  default = "./keys/id_terraform.pub"
}

variable "VPC_CIDR" {
  default = "10.0.0.0/16"
}

variable "FIRST_SUBNET_CIDR" {
  default = "10.0.1.0/24"
}

variable "SECOND_SUBNET_CIDR" {
  default = "10.0.2.0/24"
}

variable "FIRST_DC_IP" {
  default = "10.0.1.100"
}

variable "SECOND_DC_IP" {
  default = "10.0.2.100"
}

variable "ATTACK_SERVER_IP" {
  default = "10.0.1.150"
}

variable "FIRST_SERVER_IP" {
  default = "10.0.1.110"
}

variable "SECOND_SERVER_IP" {
  default = "10.0.1.200"
}

variable "THIRD_SERVER_IP" {
  default = "10.0.1.170"
}

variable "FOURTH_SERVER_IP" {
  default = "10.0.1.122"
}

variable "ELK_SERVER_IP" {
  default = "10.0.1.180"
}

variable "PUBLIC_DNS" {
  default = "1.1.1.1"
}

variable "VPN_SERVER_IP" {
  default = "10.0.1.50"
}

variable "MANAGEMENT_IPS" {
  description = "Your own /32 IP(s) allowed to manage the lab boxes (SSH/WinRM/etc). No default on purpose - set this in a terraform.tfvars file (gitignored) before running apply."
  type        = list(string)
  default     = ["CHANGEME.CHANGEME.CHANGEME.CHANGEME/32"]
}

# Declared for compatibility with the original XPN design but not currently wired
# into main.tf/deployer.py - set your own bucket name here if you use it.
variable "SSM_S3_BUCKET" {
  default = "CHANGEME_S3_BUCKET_NAME"
}

variable "ENVIRONMENT" {
  default = "notdeploylol"
}

data "aws_ami" "latest-windows-server" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Windows_Server-2019-English-Full-Base-*"]
  }
}

data "aws_ami" "primary-dc" {
  most_recent = true
  owners      = ["self"]
  count       = var.ENVIRONMENT == "deploy" ? 1 : 0
  filter {
    name   = "name"
    values = ["*-Primary-DC*"]
  }
}

data "aws_ami" "first_server" {
  most_recent = true
  owners      = ["self"]
  count       = var.ENVIRONMENT == "deploy" ? 1 : 0
  filter {
    name   = "name"
    values = ["*-First-Server*"]
  }
}

data "aws_ami" "second_server" {
  most_recent = true
  owners      = ["self"]
  count       = var.ENVIRONMENT == "deploy" ? 1 : 0
  filter {
    name   = "name"
    values = ["*-Second-Server*"]
  }
}

data "aws_ami" "third_server" {
  most_recent = true
  owners      = ["self"]
  count       = var.ENVIRONMENT == "deploy" ? 1 : 0
  filter {
    name   = "name"
    values = ["*-Third-Server*"]
  }
}

data "aws_ami" "fourth_server" {
  most_recent = true
  owners      = ["self"]
  count       = var.ENVIRONMENT == "deploy" ? 1 : 0
  filter {
    name   = "name"
    values = ["*-Fourth-Server*"]
  }
}

data "aws_ami" "attack_server" {
  most_recent = true
  owners      = ["self"]
  count       = var.ENVIRONMENT == "deploy" ? 1 : 0
  filter {
    name   = "name"
    values = ["*-Attack-Server*"]
  }
}

data "aws_ami" "vpn_server" {
  most_recent = true
  owners      = ["self"]
  count       = var.ENVIRONMENT == "deploy" ? 1 : 0
  filter {
    name   = "name"
    values = ["*-VPN-host*"]
  }
}


data "aws_ami" "elk_server" {
  most_recent = true
  owners      = ["self"]
  count       = var.ENVIRONMENT == "deploy" ? 1 : 0
  filter {
    name   = "name"
    values = ["*-ELK-Server*"]
  }
}

