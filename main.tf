# Modified version of XPN's labs setup

### Required AWS Setup

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  required_version = ">= 0.14.9"
}

# Region is configurable via var.aws_region (see vars.tf), default us-west-2
provider "aws" {
  profile = "default"
  region  = var.aws_region
}

# AWS Key Pair
resource "aws_key_pair" "terraformkey" {
  key_name   = "${terraform.workspace}-terraform-lab"
  public_key = file(var.PATH_TO_PUBLIC_KEY)
}



### AWS VPC Setup

# VPC definition
resource "aws_vpc" "lab-vpc" {
  cidr_block           = var.VPC_CIDR
  enable_dns_support   = true
  enable_dns_hostnames = true
}

# Default route for VPC to push traffic via gateway
resource "aws_route" "first-internet-route" {
  route_table_id         = aws_vpc.lab-vpc.main_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.lab-vpc-gateway.id
}

# Gateway which allows outbound and inbound internet access to the VPC (do we want this?)
resource "aws_internet_gateway" "lab-vpc-gateway" {
  vpc_id = aws_vpc.lab-vpc.id
}


### Subnets

# First subnet (10.0.1.0/24)
resource "aws_subnet" "first-vpc-subnet" {
  vpc_id = aws_vpc.lab-vpc.id

  cidr_block        = var.FIRST_SUBNET_CIDR
  availability_zone = "us-west-2a"

  tags = {
    Name = "First Subnet"
  }
}

### DHCP Setup

# Set DHCP options for delivering things like DNS servers
resource "aws_vpc_dhcp_options" "first-dhcp" {
  domain_name          = "first.local"
  domain_name_servers  = [var.FIRST_DC_IP, var.PUBLIC_DNS]
  ntp_servers          = [var.FIRST_DC_IP]
  netbios_name_servers = [var.FIRST_DC_IP]
  netbios_node_type    = 2

  tags = {
    Name = "First DHCP"
  }
}

# Associate our DHCP configuration with our VPC
resource "aws_vpc_dhcp_options_association" "first-dhcp-assoc" {
  vpc_id          = aws_vpc.lab-vpc.id
  dhcp_options_id = aws_vpc_dhcp_options.first-dhcp.id
}


### Instances


# Domain Controller (first.local)
resource "aws_instance" "primary-dc" {
  ami                         =  "${var.ENVIRONMENT == "deploy" ? data.aws_ami.primary-dc.0.image_id : var.ami_packer_build}"
  instance_type               = "t2.small"
  key_name                    = aws_key_pair.terraformkey.key_name
  associate_public_ip_address = true
  subnet_id                   = aws_subnet.first-vpc-subnet.id
  private_ip                  = var.FIRST_DC_IP
  iam_instance_profile        = "${aws_iam_instance_profile.ssm_instance_profile.name}"

  ebs_block_device {
    device_name = "/dev/sda1"
    volume_size = 65
  }

  tags = {
    workspace = "${terraform.workspace}"
    Name      = "${terraform.workspace}-Primary-DC"
  }

  vpc_security_group_ids = [
    aws_security_group.first-sg.id,
  ]
}

# First server, intial foothold
resource "aws_instance" "first_server" {
  ami                         = var.ENVIRONMENT == "deploy" ? data.aws_ami.first_server.0.image_id : var.ami_packer_build
  instance_type               = "t2.small"
  key_name                    = aws_key_pair.terraformkey.key_name
  associate_public_ip_address = true
  subnet_id                   = aws_subnet.first-vpc-subnet.id
  private_ip                  = var.FIRST_SERVER_IP
  iam_instance_profile        = "${aws_iam_instance_profile.ssm_instance_profile.name}"

  ebs_block_device {
    device_name = "/dev/sda1"
    volume_size = 65
  }


  tags = {
    workspace = "${terraform.workspace}"
    Name      = "${terraform.workspace}-First-Server"
  }

  vpc_security_group_ids = [
    aws_security_group.first-sg.id,
  ]
}

# Second server, pivot from access of first server
resource "aws_instance" "second_server" {
  ami                         = var.ENVIRONMENT == "deploy" ? data.aws_ami.second_server.0.image_id : var.ami_packer_build
  instance_type               = "t2.small"
  key_name                    = aws_key_pair.terraformkey.key_name
  associate_public_ip_address = true
  subnet_id                   = aws_subnet.first-vpc-subnet.id
  private_ip                  = var.SECOND_SERVER_IP
  iam_instance_profile        = "${aws_iam_instance_profile.ssm_instance_profile.name}"

  ebs_block_device {
    device_name = "/dev/sda1"
    volume_size = 65
  }


  tags = {
    workspace = "${terraform.workspace}"
    Name      = "${terraform.workspace}-Second-Server"
  }

  vpc_security_group_ids = [
    aws_security_group.first-sg.id,
  ]
}

# Third server, pivot from access of second server
resource "aws_instance" "third_server" {
  ami                         = var.ENVIRONMENT == "deploy" ? data.aws_ami.third_server.0.image_id : var.ami_packer_build
  instance_type               = "t2.small"
  key_name                    = aws_key_pair.terraformkey.key_name
  associate_public_ip_address = true
  subnet_id                   = aws_subnet.first-vpc-subnet.id
  private_ip                  = var.THIRD_SERVER_IP
  iam_instance_profile        = "${aws_iam_instance_profile.ssm_instance_profile.name}"

  ebs_block_device {
    device_name = "/dev/sda1"
    volume_size = 65
  }


  tags = {
    workspace = "${terraform.workspace}"
    Name      = "${terraform.workspace}-Third-Server"
  }

  vpc_security_group_ids = [
    aws_security_group.first-sg.id,
  ]
}

# Fourth server, pivot from access of third server
resource "aws_instance" "fourth_server" {
  ami                         = var.ENVIRONMENT == "deploy" ? data.aws_ami.fourth_server.0.image_id : var.ami_packer_build
  instance_type               = "t2.small"
  key_name                    = aws_key_pair.terraformkey.key_name
  associate_public_ip_address = true
  subnet_id                   = aws_subnet.first-vpc-subnet.id
  private_ip                  = var.FOURTH_SERVER_IP
  iam_instance_profile        = "${aws_iam_instance_profile.ssm_instance_profile.name}"

  ebs_block_device {
    device_name = "/dev/sda1"
    volume_size = 65
  }


  tags = {
    workspace = "${terraform.workspace}"
    Name      = "${terraform.workspace}-Fourth-Server"
  }

  vpc_security_group_ids = [
    aws_security_group.first-sg.id,
  ]
}

# ELK Server - NEED TO UPDATE AMI IF STATEMENT EVENTUALLY
resource "aws_instance" "elk_server" {
  ami                         = var.ENVIRONMENT == "deploy" ? data.aws_ami.elk_server.0.image_id : "ami-01f8a74810b880125"
  instance_type               = "t2.large"
  key_name                    = aws_key_pair.terraformkey.key_name
  associate_public_ip_address = true
  subnet_id                   = aws_subnet.first-vpc-subnet.id
  private_ip                  = var.ELK_SERVER_IP
  iam_instance_profile        = "${aws_iam_instance_profile.ssm_instance_profile.name}"

  ebs_block_device {
    device_name = "/dev/sda1"
    volume_size = 50
  }

  tags = {
    workspace = "${terraform.workspace}"
    Name      = "${terraform.workspace}-ELK-Server"
  }

  vpc_security_group_ids = [
    aws_security_group.first-sg.id,
  ]
}


#VPN host
resource "aws_instance" "vpn_host" {
  ami			      = var.ENVIRONMENT == "deploy" ? data.aws_ami.vpn_server.0.image_id : "ami-01f8a74810b880125"
  instance_type		      = "t2.micro"
  key_name                    = aws_key_pair.terraformkey.key_name
  associate_public_ip_address = true
  subnet_id		      = aws_subnet.first-vpc-subnet.id
  private_ip 		      = var.VPN_SERVER_IP
  iam_instance_profile 	      = "${aws_iam_instance_profile.ssm_instance_profile.name}"

  ebs_block_device {
    device_name = "/dev/sda1"
    volume_size = 50
  }


  tags = {
    workspace ="${terraform.workspace}"
    Name ="${terraform.workspace}-VPN-host"
  }
  vpc_security_group_ids = [
    aws_security_group.vpn-sg.id,
  ]
}

# Kali Attack box
resource "aws_instance" "attack-kali" {
  ami                         = var.ENVIRONMENT == "deploy" ? data.aws_ami.attack_server.0.image_id : "ami-04c107ffa12bd5ac2"
  instance_type               = "t2.medium"
  key_name                    = aws_key_pair.terraformkey.key_name
  associate_public_ip_address = true
  subnet_id                   = aws_subnet.first-vpc-subnet.id
  private_ip                  = var.ATTACK_SERVER_IP
  iam_instance_profile        = "${aws_iam_instance_profile.ssm_instance_profile.name}"

  ebs_block_device {
    device_name = "/dev/xvda"
    volume_size = 50
  }


  tags = {
    workspace = "${terraform.workspace}"
    Name      = "${terraform.workspace}-Attack-Server"
  }

  vpc_security_group_ids = [
    aws_security_group.first-sg.id,
  ]
}



### IAM Setup

# IAM Role required to access SSM from EC2
resource "aws_iam_role" "ssm_role" {
  name               = "${terraform.workspace}_ssm_role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "ssm_role_policy" {
  role       = "${aws_iam_role.ssm_role.name}"
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
}

resource "aws_iam_instance_profile" "ssm_instance_profile" {
  name  = "${terraform.workspace}_ssm_instance_profile"
  role = "${aws_iam_role.ssm_role.name}"
}


### AWS Security Groups


# Security group for first.local
resource "aws_security_group" "first-sg" {
  vpc_id = aws_vpc.lab-vpc.id

  # Allow second zone to first
  ingress {
    protocol    = "-1"
    cidr_blocks = [var.SECOND_SUBNET_CIDR]
    from_port   = 0
    to_port     = 0
  }

  ingress {
    protocol    = "-1"
    cidr_blocks = [var.FIRST_SUBNET_CIDR]
    from_port   = 0
    to_port     = 0
  }

  # Allow management from our IP
  ingress {
    protocol    = "-1"
    cidr_blocks = var.MANAGEMENT_IPS
    from_port   = 0
    to_port     = 0
  }

  # Allow global outbound
  egress {
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    to_port     = 0
  }
}


# Security group for the vpn box
resource "aws_security_group" "vpn-sg" {
  vpc_id = aws_vpc.lab-vpc.id

  # Allow second zone to first
  ingress {
    protocol    = "-1"
    cidr_blocks = [var.SECOND_SUBNET_CIDR]
    from_port   = 0
    to_port     = 0
  }

  ingress {
    protocol    = "-1"
    cidr_blocks = [var.FIRST_SUBNET_CIDR]
    from_port   = 0
    to_port     = 0
  }

  # Allow vpn from anywhere
  ingress {
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 1194
    to_port     = 1194
  }

  # Allow vpn from anywhere
  ingress {
    protocol    = "tcp"
    cidr_blocks = var.MANAGEMENT_IPS
    from_port   = 22
    to_port     = 22
  }
  
  ingress {
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 443
    to_port     = 443
  }
  
  # Allow global outbound
  egress {
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    to_port     = 0
  }
}

### Kali Box Configuration

# Kali box configuration, commented out for now, do we even need this tbh?
/*
resource "null_resource" "attack-server-setup" {
  connection {
    type        = "ssh"
    host        = aws_instance.attack-server.public_ip
    user        = "kali"
    port        = "22"
    private_key = file(var.PATH_TO_PRIVATE_KEY)
    agent       = false
  }

  provisioner "remote-exec" {
    inline = [
      "sudo apt update",
      
      # Install dotnet
      "wget https://packages.microsoft.com/config/debian/10/packages-microsoft-prod.deb -O packages-microsoft-prod.deb",
      "sudo dpkg -i packages-microsoft-prod.deb",
      "sudo apt-get update",
      "sudo apt-get install -y apt-transport-https",
      "sudo apt-get update",
      
      # Install Covenant Stable
      "sudo apt-get install -y dotnet-sdk-3.1",
      "sudo apt-get install -y git",
      "git clone --recurse-submodules https://github.com/cobbr/Covenant",
      
      # Install Covenant Dev
      #"sudo apt-get install -y dotnet-sdk-5.0",
      #"git clone -b dev --recurse-submodules https://github.com/cobbr/Covenant",
      
      # Install PoshC2
      #"git clone https://github.com/nettitude/PoshC2.git",
      #"cd PoshC2",
      #"sudo ./Install.sh -b master -p /home/admin/PoshC2"
      #"cd ../"
      
      # Install Impacket
      "sudo apt install -y python3-pip",
      "git clone https://github.com/SecureAuthCorp/impacket.git",
      "cd impacket",
      "sudo python3 -m pip install --upgrade pip",
      "sudo python3 -m pip install .",
      "cd ../"
    ]
  }
}
*/


output "primary-dc_ip" {
  value       = "${aws_instance.primary-dc.public_ip}"
  description = "Public IP of Primary-DC"
}

output "attacker_box_ip" {
  value       = "${aws_instance.attack-kali.public_ip}"
  description = "Public IP of Attack-Kali"
}

output "first-server-ip" {
  value       = "${aws_instance.first_server.public_ip}"
  description = "Public IP of First-Server"
}
output "second-server-ip" {
  value       = "${aws_instance.second_server.public_ip}"
  description = "Public IP of Second-Server"
}

output "third-server-ip" {
  value       = "${aws_instance.third_server.public_ip}"
  description = "Public IP of Third-Server"
}

output "fourth-server-ip" {
  value       = "${aws_instance.fourth_server.public_ip}"
  description = "Public IP of Fourth-Server"
}

output "management-ip"{
  value       = var.MANAGEMENT_IPS
  description = "IP Addresses whitelisted for management"
}

output "vpn-host-ip"{
  value       = "${aws_instance.vpn_host.public_ip}"
  description = "Public IP of the VPN Server"
}

output "elk-server-ip"{
  value       = "${aws_instance.elk_server.public_ip}"
  description = "Public IP of the VPN Server"
}








