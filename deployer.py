#!/usr/bin/env python3
import json, os, time, boto3, botocore, threading, argparse, sys
from re import A
from multiprocessing import Pool
from subprocess import Popen, PIPE
import re

#max_labs is set to prevent the script trying to make more machines then possible under the accounts AWS limits
#Note that each lab requires 9 vCPUs, and 1 VPC network
#Check your aws limits to ensure you have enough space for your chosen amount of labs
#For example 50 labs would require 450 vCPUs and 50 VPC networks
max_labs = 50

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def ec2checkerstaging():
    # Region is read from AWS_REGION (defaults to us-west-2); see firstrun().
    session = boto3.Session(region_name=os.environ.get("AWS_REGION", "us-west-2"))
    ec2 = session.resource('ec2')
    client = boto3.client('ec2')
    instance_filter = [{'Name': 'tag:workspace', 'Values': ['staging']},{'Name': 'instance-state-name', 'Values': ['running']}]
    instances = ec2.instances.filter(Filters=instance_filter)
    inst = []
    for instance in instances:
        inst.append(instance.id)
    
    try:
        waiter = client.get_waiter('system_status_ok')
        waiter.wait(InstanceIds=inst,
            WaiterConfig={
            'Delay': 20,
            'MaxAttempts': 100,
        })
        waiter2 = client.get_waiter('instance_status_ok')
        waiter2.wait(InstanceIds=inst,
            WaiterConfig={
            'Delay': 20,
            'MaxAttempts': 100
        })
    except botocore.exceptions.WaitError as e:
        print(e)



def firstrun():

    # Region is read from AWS_REGION (defaults to us-west-2) to match
    # var.aws_region in vars.tf / main.tf; set AWS_REGION to deploy elsewhere.
    session = boto3.Session(region_name=os.environ.get("AWS_REGION", "us-west-2"))
    ec2 = session.resource('ec2')
    client = boto3.client('ec2')
    os.system("chmod 400 keys/id_terraform")

    #Terraform new, staging workspace will be created, to be imaged
    print("(*) Deploying terraform stager...\n")
    
    #Checking for existing 'staging' workspace
    checkStaging = os.popen("terraform workspace list").read()
    if checkStaging.find("staging"):
        print(bcolors.WARNING + "(!) Previous instance of staging workspace found, do you want to delete? (Y/N)")
        userdelete = input()
        if str(userdelete).lower() == "yes" or str(userdelete).lower() == "y":
            os.system("terraform workspace select staging")
            os.system("terraform destroy -auto-approve")
        elif str(userdelete).lower() == "no" or str(userdelete).lower() == "n":
            os.system("terraform workspace select staging")
        else:
            print("(!) Please enter yes or no")
            exit()
    else:
        os.system("terraform workspace new staging")

    #Let Terraform build
    os.system("terraform apply -auto-approve")
    os.system('terraform output -json > terraform_states/terraform_out.json')
    print("\n(!) Terraform deployed succesfully\n")

    #Populate "Inventory" file - aka array in memory
    terraform_file = 'terraform_states/terraform_out.json'
    if not os.path.exists(terraform_file):
        print("(!) Terraform file does not exist, cannot parse!")
        exit()
    
    #Extract ips from terraform json output to hashmap
    terraform_json = json.loads(open(terraform_file).read())
    TerraformIPs = {
        "attackerbox" : terraform_json["attacker_box_ip"]["value"],
        "firstserver" : terraform_json["first-server-ip"]["value"],
        "secondserver" : terraform_json["second-server-ip"]["value"],
        "thirdserver" : terraform_json["third-server-ip"]["value"],
        "fourthserver" : terraform_json["fourth-server-ip"]["value"],
        "primaryserver" : terraform_json["primary-dc_ip"]["value"],
        "vpnserver" : terraform_json["vpn-host-ip"]["value"],
        "elkserver" : terraform_json["elk-server-ip"]["value"]
    }

    print("(!) The script will now pause to wait for systems and instance statuses to be okay, this can take upwards of 10 minutes...")
    time.sleep(10)
    ec2checkerstaging()
    time.sleep(10)

    print("(!) Terraform finished, pausing execution; it is recommended to check the output for any errors")
    print(bcolors.WARNING + "(!) Press enter to continue to the ansible process, expect alot of output")
    cont = input() 

 

    #Setup ansible variables and commands
    #TODO: Can we optimize this?
    #TODO: Integrate Ansible vault to remove password?
    print("(!) Applying ansible, this will take a while...\n")
    print("(*) Keep an eye out for errors, there is no error handling yet...\n")
    ansible_user = "lab-admin"
    ansible_password = os.environ.get("LAB_ADMIN_PASSWORD", "CHANGEME_LAB_ADMIN_PASSWORD")  # set via env var, do not hardcode
    DCCommand = "ansible-playbook ansible/domain-playbooks/AD-DC_Create.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    UserCreatorCommand = "ansible-playbook ansible/domain-playbooks/User-Creator.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box1Command = "ansible-playbook ansible/domain-playbooks/Box1.yml -i " + TerraformIPs["firstserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box2Command = "ansible-playbook ansible/domain-playbooks/Box2.yml -i " + TerraformIPs["secondserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box3Command = "ansible-playbook ansible/domain-playbooks/Box3.yml -i " + TerraformIPs["thirdserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box4Command = "ansible-playbook ansible/domain-playbooks/Box4.yml -i " + TerraformIPs["fourthserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    KaliCommand = "ansible-playbook ansible/infra-playbooks/Kali-Server.yml -i " + TerraformIPs["attackerbox"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'kali','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""
    AvOffCommand = "ansible-playbook ansible/domain-playbooks/DC-AV-Off.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""      
    VPNCommand = "ansible-playbook ansible/infra-playbooks/VPN-Setup.yml -i " + TerraformIPs["vpnserver"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'ubuntu','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""
    ELKCommand = "ansible-playbook ansible/infra-playbooks/ELK-Server.yml -i " +TerraformIPs["elkserver"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'ubuntu','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""

    #TODO: Can we optimize this - do we care? its messy but it works for the one imaging run we have to do.
    print("\n\n(!) Setting up ad create playbook...\n")
    os.system(DCCommand)
    print("\n\n(!) Setting up user adder playbook...\n")
    os.system(UserCreatorCommand)
    print("\n\n(!) Setting up Box1 playbook...\n")
    proc2 = Popen(['/bin/sh', '-c', Box1Command])
    print("\n\n(!) Setting up Box2 playbook...\n")
    proc3 = Popen(['/bin/sh', '-c', Box2Command])
    print("\n\n(!) Setting up Box3 playbook...\n")
    proc4 = Popen(['/bin/sh', '-c', Box3Command])
    print("\n\n(!) Setting up Box4 playbook...\n")
    proc25 = Popen(['/bin/sh', '-c', Box4Command])
    proc2.wait()
    proc3.wait()
    proc4.wait()
    proc25.wait()
    print("\n\n(!) Setting up kali playbook...\n")
    proc7 = Popen(['/bin/sh', '-c', KaliCommand])
    print("\n\n(!) Setting up dc av off playbook...\n")
    proc8 = Popen(['/bin/sh', '-c', AvOffCommand])
    print("\n\n(!) Setting up vpn playbook...\n")
    proc9 = Popen(['/bin/sh', '-c', VPNCommand])
    print("\n\n(!) Setting up ELK playbook...\n")
    proc10 = Popen(['/bin/sh', '-c', ELKCommand])
    proc7.wait()
    proc8.wait()
    proc9.wait()
    proc10.wait()



    time.sleep(10)

    os.system("cp ansible/infra-playbooks/client.ovpn/%s/home/ubuntu/client.ovpn vpns/labstaging.ovpn" % str(TerraformIPs["vpnserver"]))
    os.system("cp ansible/infra-playbooks/support.ovpn/%s/home/ubuntu/support.ovpn vpns/support.ovpn" % str(TerraformIPs["vpnserver"]))

    print("(!) Setting up logging")
    Box1Logging = "ansible-playbook ansible/logging.yml -i " + TerraformIPs["firstserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box2Logging = "ansible-playbook ansible/logging.yml -i " + TerraformIPs["secondserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box3Logging = "ansible-playbook ansible/logging.yml -i " + TerraformIPs["thirdserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box4Logging = "ansible-playbook ansible/logging.yml -i " + TerraformIPs["fourthserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    BoxDCLogging = "ansible-playbook ansible/logging.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    proc11 = Popen(['/bin/sh', '-c', Box1Logging])
    proc12 = Popen(['/bin/sh', '-c', Box2Logging])
    proc13 = Popen(['/bin/sh', '-c', Box3Logging])
    proc18 = Popen(['/bin/sh', '-c', Box4Logging])
    proc14 = Popen(['/bin/sh', '-c', BoxDCLogging])
    proc11.wait()
    proc12.wait()
    proc13.wait()
    proc14.wait()
    proc18.wait()

    print("(!) Ansible playbooks finished, pausing execution; it is recommended to check the output for any errors")
    print(bcolors.WARNING + "(!) Press enter to continue to the imaging process, expect alot of output")
    cont = input()

def imager():
    print(bcolors.OKGREEN + "\n\n(*) Starting Imager...\n")

    ec2 = boto3.resource('ec2')
    response = ec2.instances.filter(Filters=[{'Name': 'tag:workspace', 'Values': ['staging']},{'Name': 'instance-state-name', 'Values': ['running']}])
    ec5 = boto3.client('ec2')

    #Delete any old lab AMis
    filters =[{'Name':'description','Values':['Lab Imager']}]
    amis = ec5.describe_images(Filters=filters)

    for ami in amis['Images']:
        print(ami)
        ami_id = ami['ImageId']
        print("deleting -> " + ami_id)
        ec5.deregister_image(ImageId=ami_id)

    #Imaging process for current staging labs
    for instance in response:
        print(instance)
        for kv in instance.tags:
            if kv["Key"] == "Name": 
                print("====[ Creating AMI For {0}]====".format(kv["Value"]))
                name = kv["Value"] + "-{0}".format(time.time())
                instance.create_image(Name=name,Description="Lab Imager")

    print(bcolors.OKGREEN + "\n\n(!) Imaging finished, please wait for AMIs to become ready")
    waiter = ec5.get_waiter('image_available')
    waiter.wait(WaiterConfig={
        'Delay': 20,
        'MaxAttempts': 50
    })
    print("(*) Images ready for use")

def deploy(i):
    command0 = ("export TF_WORKSPACE=lab" + str(i))
    command1 = ('terraform apply -auto-approve --var ENVIRONMENT=deploy')
    command2 = ('terraform output -json > terraform_states/terraform_out_lab_'+str(i)+'.json')
    command3 = (command0  + '; ' + command1 + '; ' + command2)

    print("(!) Deploying lab" + str(i))
    child_shell = Popen(['/bin/sh', '-c', command3])

    print("(!) The script will now pause to wait for systems and instance statuses to be okay, this can take upwards of 10 minutes...")
    time.sleep(20)
    ec2checkerstaging()
    time.sleep(10)

def waitdeploy():
    time.sleep(30)
    client = boto3.client('ec2')
    waiter = client.get_waiter('system_status_ok')
    waiter.wait(WaiterConfig={
        'Delay': 20,
        'MaxAttempts': 500
    })
    waiter = client.get_waiter('instance_status_ok')
    waiter.wait(WaiterConfig={
        'Delay': 20,
        'MaxAttempts': 500
    })


def deployer(numOfLabs):
    with Pool(max_labs) as p:
        results = p.map(deploy, range(1, numOfLabs + 1))

def redeploylab(i):
    deploy(i)

def refresh(numOfLabs):
    with Pool(max_labs) as p:
        results = p.map(refresher, range(1, numOfLabs + 1))

def fix(numOfLabs):
    with Pool(max_labs) as p:
        results = p.map(fixer, range(1, numOfLabs + 1))


def fixer(i):
    #Populate Inventory file
    terraform_file = 'terraform_states/terraform_out_lab_'+str(i)+'.json'
    if not os.path.exists(terraform_file):
        print("Terraform file does not exist, cannot parse!")
        exit() 
        #Extract ips from terraform json output to hashmap
    terraform_json = json.loads(open(terraform_file).read())
    TerraformIPs = {
        "attackerbox" : terraform_json["attacker_box_ip"]["value"],
        "firstserver" : terraform_json["first-server-ip"]["value"],
        "secondserver" : terraform_json["second-server-ip"]["value"],
        "thirdserver" : terraform_json["third-server-ip"]["value"],
        "fourthserver" : terraform_json["fourth-server-ip"]["value"],
        "primaryserver" : terraform_json["primary-dc_ip"]["value"],
        "vpnserver" : terraform_json["vpn-host-ip"]["value"],
        "elkserver" : terraform_json["elk-server-ip"]["value"]
    }
    VPNCommand = "ansible-playbook fixer/infra-playbooks/VPN-Setup.yml -i " + TerraformIPs["vpnserver"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'ubuntu','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""
    ELKCommand = "ansible-playbook fixer/infra-playbooks/ELK-Server.yml -i " +TerraformIPs["elkserver"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'ubuntu','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""
    KaliCommand = "ansible-playbook fixer/infra-playbooks/Kali-Server.yml -i " + TerraformIPs["attackerbox"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'kali','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""

    print("\n\n(!) Fixing VPN for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', VPNCommand])
    proc.wait()

    print("\n\n(!) Fixing ELK for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', ELKCommand])
    proc.wait()
    
    print("\n\n(!) Fixing Kali for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', KaliCommand])
    proc.wait()

    os.system("cp fixer/infra-playbooks/labclient.ovpn/%s/home/ubuntu/labclient.ovpn vpns/lab%sclient.ovpn" % (str(TerraformIPs["vpnserver"]), str(i)))
    os.system("cp fixer/infra-playbooks/labsupport.ovpn/%s/home/ubuntu/labsupport.ovpn vpns/lab%ssupport.ovpn" % (str(TerraformIPs["vpnserver"]), str(i)))


def refresher(i):
    #Populate Inventory file
    terraform_file = 'terraform_states/terraform_out_lab_'+str(i)+'.json'
    if not os.path.exists(terraform_file):
        print("Terraform file does not exist, cannot parse!")
        exit()

    #Extract ips from terraform json output to hashmap
    terraform_json = json.loads(open(terraform_file).read())
    TerraformIPs = {
        "attackerbox" : terraform_json["attacker_box_ip"]["value"],
        "firstserver" : terraform_json["first-server-ip"]["value"],
        "secondserver" : terraform_json["second-server-ip"]["value"],
        "thirdserver" : terraform_json["third-server-ip"]["value"],
        "fourthserver" : terraform_json["fourth-server-ip"]["value"],
        "primaryserver" : terraform_json["primary-dc_ip"]["value"],
        "vpnserver" : terraform_json["vpn-host-ip"]["value"],
        "elkserver" : terraform_json["elk-server-ip"]["value"]
    }
    
    #Select relevent lab workspace, we shouldnt need this anymore uncomment if things break
    #os.system('terraform workspace select lab' + str(i))

    ansible_user = "lab-admin"
    ansible_password = os.environ.get("LAB_ADMIN_PASSWORD", "CHANGEME_LAB_ADMIN_PASSWORD")  # set via env var, do not hardcode
    DCCommand = "ansible-playbook ansible/domain-playbooks/AD-DC_Create.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    UserCreatorCommand = "ansible-playbook ansible/domain-playbooks/User-Creator.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box1Command = "ansible-playbook ansible/domain-playbooks/Box1.yml -i " + TerraformIPs["firstserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box2Command = "ansible-playbook ansible/domain-playbooks/Box2.yml -i " + TerraformIPs["secondserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box3Command = "ansible-playbook ansible/domain-playbooks/Box3.yml -i " + TerraformIPs["thirdserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    Box4Command = "ansible-playbook ansible/domain-playbooks/Box4.yml -i " + TerraformIPs["fourthserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
    KaliCommand = "ansible-playbook ansible/infra-playbooks/Kali-Server.yml -i " + TerraformIPs["attackerbox"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'kali','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""
    AvOffCommand = "ansible-playbook ansible/domain-playbooks/DC-AV-Off.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""      
    VPNCommand = "ansible-playbook ansible/infra-playbooks/VPN-Setup.yml -i " + TerraformIPs["vpnserver"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'ubuntu','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""
    ELKCommand = "ansible-playbook ansible/infra-playbooks/ELK-Server.yml -i " +TerraformIPs["elkserver"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'ubuntu','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""

    print("\n\n(!) Refreshing AD Domain Controller for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', DCCommand])
    proc.wait()

    print("\n\n(!) Refreshing user creator playbook for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', UserCreatorCommand])
    proc.wait()

    print("\n\n(!) Refreshing Box 1 playbook for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', Box1Command])
    proc.wait()

    print("\n\n(!) Refreshing Box 2 playbook for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', Box2Command])
    proc.wait()

    print("\n\n(!) Refreshing Box 3 playbook for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', Box3Command])
    proc.wait()
    
    print("\n\n(!) Refreshing Box 4 playbook for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', Box4Command])
    proc.wait()

    print("\n\n(!) Refreshing Kali playbook for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', KaliCommand])
    proc.wait()
 
    print("\n\n(!) Refreshing AV DC Off playbook for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', AvOffCommand])
    proc.wait()

    print("\n\n(!) Refreshing VPN playbook for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', VPNCommand])
    proc.wait()

    print("\n\n(!) Refreshing ELK playbook for lab"+str(i)+"...\n")
    proc = Popen(['/bin/sh', '-c', ELKCommand])
    proc.wait()

    os.system("cp ansible/infra-playbooks/client.ovpn/%s/home/ubuntu/client.ovpn vpns/lab%sclient.ovpn" % (str(TerraformIPs["vpnserver"]), str(i)))
    os.system("cp ansible/infra-playbooks/support.ovpn/%s/home/ubuntu/support.ovpn vpns/lab%ssupport.ovpn" % (str(TerraformIPs["vpnserver"]), str(i)))

    print("(*) Lab" + str(i) + " Fully Refreshed")


def destroy(numOfLabs):
    with Pool(max_labs) as p:
        results = p.map(destroyer, range(1, numOfLabs + 1))

def destroyer(i):
    command0 = ("export TF_WORKSPACE=lab" + str(i))
    command1 = ('terraform destroy -auto-approve')
    command2 = (command0 + ';' + command1)
    print("Destroying lab" + str(i))    
    child_shell = Popen(['/bin/sh', '-c' , command2])


def restartlab(i):
    #TODO: Restart N lab box function
    a = "lab" + str(i)
    session = boto3.Session(region_name=os.environ.get("AWS_REGION", "us-west-2"))
    ec2 = session.resource('ec2')
    client = boto3.client('ec2')
    instance_filter = [{'Name': 'tag:workspace', 'Values': [a]},{'Name': 'instance-state-name', 'Values': ['running']}]
    instances = ec2.instances.filter(Filters=instance_filter)
    inst = []
    for instance in instances:
        inst.append(instance.id)
    for i in inst:
        response = client.reboot_instances(InstanceIds=[i])
        print(response)

def refreshlab(i):
    refresher(i)

def fixlab(i):
    fixer(i)

def destroylab(i):
    command0 = ("export TF_WORKSPACE=lab" + str(i))
    command1 = ('terraform destroy --auto-approve')
    command3 = (command0  + '; ' + command1)

    print("(!) Destroying " + str(i))
    child_shell = Popen(['/bin/sh', '-c', command3])



def packer():
    print(bcolors.OKGREEN + "\n\n(*) Starting Packer...\n")
    print(bcolors.OKGREEN + "\n\n(*) Creating AMI Image...\n")
    packercommand = "packer build packer/config.pkr.hcl"
    os.system(packercommand)
    print(bcolors.OKGREEN + "\n\n(*) Image created, make sure to update the AMI number in vars.tf \n")


def redeployer(machine, workspace):
    if "staging" in workspace:
        command0 = ("terraform workspace select " + str(workspace))
        command1 = ('terraform apply -replace="'+ str(machine) + '" --auto-approve')
        command2 = (command0 + ';' + command1)
        print("(!) Rebuilding machine" + str(machine) + " in workspace " + str(workspace))    
        proc = Popen(['/bin/sh', '-c' , command2])
        proc.wait()
    elif "lab" in workspace:
        command0 = ("terraform workspace select " + str(workspace))
        command1 = ('terraform apply -replace="'+ str(machine) + '" --auto-approve --var ENVIRONMENT=deploy')
        command2 = (command0 + ';' + command1)
        print("(!) Rebuilding machine" + str(machine) + " in workspace " + str(workspace))    
        proc = Popen(['/bin/sh', '-c' , command2])
        proc.wait()

    ansible_user = "lab-admin"
    ansible_password = os.environ.get("LAB_ADMIN_PASSWORD", "CHANGEME_LAB_ADMIN_PASSWORD")  # set via env var, do not hardcode
    TerraformIPs = {}

    if "staging" in workspace:
        os.system('terraform output -json > terraform_states/terraform_out.json')
        terraform_file = 'terraform_states/terraform_out.json'
        terraform_json = json.loads(open(terraform_file).read())
        TerraformIPs = {
            "attackerbox" : terraform_json["attacker_box_ip"]["value"],
            "firstserver" : terraform_json["first-server-ip"]["value"],
            "secondserver" : terraform_json["second-server-ip"]["value"],
            "thirdserver" : terraform_json["third-server-ip"]["value"],
            "fourthserver" : terraform_json["fourth-server-ip"]["value"],
            "primaryserver" : terraform_json["primary-dc_ip"]["value"],
            "vpnserver" : terraform_json["vpn-host-ip"]["value"],
            "elkserver" : terraform_json["elk-server-ip"]["value"]
        }
    elif "lab" in workspace:
        i = re.split('(\d+)',workspace)
        command0 = ("terraform workspace select " + str(workspace))
        command1 = ('terraform output -json > terraform_states/terraform_out_lab_'+str(i[1])+'.json')
        command2 = (command0 + ';' + command1)
        proc = Popen(['/bin/sh', '-c' , command2])
        proc.wait()
        terraform_file = 'terraform_states/terraform_out_lab_'+str(i[1])+'.json'
        terraform_json = json.loads(open(terraform_file).read())
        TerraformIPs = {
            "attackerbox" : terraform_json["attacker_box_ip"]["value"],
            "firstserver" : terraform_json["first-server-ip"]["value"],
            "secondserver" : terraform_json["second-server-ip"]["value"],
            "thirdserver" : terraform_json["third-server-ip"]["value"],
            "fourthserver" : terraform_json["fourth-server-ip"]["value"],
            "primaryserver" : terraform_json["primary-dc_ip"]["value"],
            "vpnserver" : terraform_json["vpn-host-ip"]["value"],
            "elkserver" : terraform_json["elk-server-ip"]["value"]
        }
    print("(!) The script will halt for a few minutes to allow the box to come up")
    time.sleep(60)
    ec2checkerstaging()
    time.sleep(60)
    print("(!) Machine rebuilt, configuring ansible...")
    if "first" in machine:
        Box1Command = "ansible-playbook ansible/domain-playbooks/Box1.yml -i " + TerraformIPs["firstserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(Box1Command)
        UserCreatorCommand = "ansible-playbook ansible/domain-playbooks/User-Creator.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(UserCreatorCommand)
        Box1Logging = "ansible-playbook ansible/logging.yml -i " + TerraformIPs["firstserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(Box1Logging)
    elif "second" in machine:
        Box2Command = "ansible-playbook ansible/domain-playbooks/Box2.yml -i " + TerraformIPs["secondserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(Box2Command)
        UserCreatorCommand = "ansible-playbook ansible/domain-playbooks/User-Creator.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(UserCreatorCommand)
        Box2Logging = "ansible-playbook ansible/logging.yml -i " + TerraformIPs["secondserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(Box2Logging)
    elif "third" in machine:
        Box3Command = "ansible-playbook ansible/domain-playbooks/Box3.yml -i " + TerraformIPs["thirdserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(Box3Command)
        UserCreatorCommand = "ansible-playbook ansible/domain-playbooks/User-Creator.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(UserCreatorCommand)
        Box3Logging = "ansible-playbook ansible/logging.yml -i " + TerraformIPs["thirdserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(Box3Logging)
    elif "fourth" in machine:
        Box4Command = "ansible-playbook ansible/domain-playbooks/Box4.yml -i " + TerraformIPs["fourthserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(Box4Command)
        UserCreatorCommand = "ansible-playbook ansible/domain-playbooks/User-Creator.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(UserCreatorCommand)
        Box4Logging = "ansible-playbook ansible/logging.yml -i " + TerraformIPs["fourthserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(Box4Logging)
    elif "kali" in machine:
        KaliCommand = "ansible-playbook ansible/infra-playbooks/Kali-Server.yml -i " + TerraformIPs["attackerbox"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'kali','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""
        os.system(KaliCommand)
    elif "elk" in machine:
        ELKCommand = "ansible-playbook ansible/infra-playbooks/ELK-Server.yml -i " +TerraformIPs["elkserver"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'ubuntu','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""
        os.system(ELKCommand)
    elif "vpn" in machine:
        VPNCommand = "ansible-playbook ansible/infra-playbooks/VPN-Setup.yml -i " + TerraformIPs["vpnserver"] + ", --private-key keys/id_terraform --extra-vars \"{'ansible_ssh_private_key':'keys/id_terraform','ansible_ssh_user':'ubuntu','ansible_connection':'ssh','ansible_python_interpreter':'/usr/bin/python3','host_key_checking':'false','ansible_ssh_common_args':'-o StrictHostKeyChecking=no'}\""
        os.system(VPNCommand)
        if "staging" in workspace:
            os.system("cp ansible/infra-playbooks/client.ovpn/%s/home/ubuntu/client.ovpn vpns/labstaging.ovpn" % str(TerraformIPs["vpnserver"]))
            os.system("cp ansible/infra-playbooks/support.ovpn/%s/home/ubuntu/support.ovpn vpns/support.ovpn" % str(TerraformIPs["vpnserver"]))
        elif "lab" in workspace:
            i = re.split('(\d+)',workspace)
            os.system("cp ansible/infra-playbooks/client.ovpn/%s/home/ubuntu/client.ovpn vpns/lab%sclient.ovpn" % str(TerraformIPs["vpnserver"]), str(i))
            os.system("cp ansible/infra-playbooks/support.ovpn/%s/home/ubuntu/support.ovpn vpns/lab%ssupport.ovpn" % str(TerraformIPs["vpnserver"]), str(i))
    elif "primary-dc" in machine:
        DCCommand = "ansible-playbook ansible/domain-playbooks/AD-DC_Create.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(DCCommand)
        UserCreatorCommand = "ansible-playbook ansible/domain-playbooks/User-Creator.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(UserCreatorCommand)
        BoxDCLogging = "ansible-playbook ansible/logging.yml -i " + TerraformIPs["primaryserver"] + ", --extra-vars \"{'ansible_user':'" + ansible_user +"','ansible_password':'"+ansible_password+"','ansible_connection':'winrm', 'ansible_winrm_transport':'ntlm','ansible_winrm_server_cert_validation':'ignore'}\""
        os.system(BoxDCLogging)
    else:
        os.print("Ansible doesnt exist for this machine")






print(bcolors.OKCYAN+ 
"""
▓█████▄ ▓█████  ██▓███   ██▓     ▒█████  ▓██   ██▓▓█████  ██▀███  
▒██▀ ██▌▓█   ▀ ▓██░  ██▒▓██▒    ▒██▒  ██▒ ▒██  ██▒▓█   ▀ ▓██ ▒ ██▒
░██   █▌▒███   ▓██░ ██▓▒▒██░    ▒██░  ██▒  ▒██ ██░▒███   ▓██ ░▄█ ▒
░▓█▄   ▌▒▓█  ▄ ▒██▄█▓▒ ▒▒██░    ▒██   ██░  ░ ▐██▓░▒▓█  ▄ ▒██▀▀█▄  
░▒████▓ ░▒████▒▒██▒ ░  ░░██████▒░ ████▓▒░  ░ ██▒▓░░▒████▒░██▓ ▒██▒
 ▒▒▓  ▒ ░░ ▒░ ░▒▓▒░ ░  ░░ ▒░▓  ░░ ▒░▒░▒░    ██▒▒▒ ░░ ▒░ ░░ ▒▓ ░▒▓░
 ░ ▒  ▒  ░ ░  ░░▒ ░     ░ ░ ▒  ░  ░ ▒ ▒░  ▓██ ░▒░  ░ ░  ░  ░▒ ░ ▒░
 ░ ░  ░    ░   ░░         ░ ░   ░ ░ ░ ▒   ▒ ▒ ░░     ░     ░░   ░ 
   ░       ░  ░             ░  ░    ░ ░   ░ ░        ░  ░   ░     
 ░                                        ░ ░                     
 \n""")

parser = argparse.ArgumentParser(description="Training labs deployment", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-p", "--packer", default=False, action="store_true", help="Create packer ami for rest of script")
parser.add_argument("-f", "--first", default=False, action="store_true", help="First run of the script")
parser.add_argument("-i", "--imager", default=False, action="store_true", help="Perform imaging of the AMI's")
parser.add_argument("-d","--deploy", default=0, type=int, choices=range(1, max_labs + 1), metavar='INT[1,%s]' % max_labs, help="Deploy N labs")
parser.add_argument("-r","--refresh", default=0, type=int, choices=range(1, max_labs + 1), metavar='INT[1,%s]' % max_labs, help="Refresh N labs")
parser.add_argument("-a", "--all", default=0, type=int, choices=range(1, max_labs + 1), metavar='INT[1,%s]' % max_labs, help="Run all build commands (excluding packer) in order for N labs")
parser.add_argument("--destroy", default=0, type=int, choices=range(1, max_labs + 1), metavar='INT[1,%s]' % max_labs, help="Destroy N labs")
parser.add_argument("--restartlab", default=0, type=str,  metavar='labx', help="Restart lab N (Input example: 1")
parser.add_argument("--refreshlab", default=0, type=int, choices=range(1, max_labs + 1),  metavar='INT[1,%s]' % max_labs, help="Refresh lab N")
parser.add_argument("--destroylab", default=0, type=str,  metavar='labx', help="Destroy lab N (Input example: 1")
parser.add_argument("--redeploylab", default=0, type=str,  metavar='labx', help="Redeploy lab N (Input example: 1" )
parser.add_argument('--redeployer', nargs=2, metavar=('machine','workspace'), type=str, help="Redeploy and configure machine X in workspace Y (X,Y)")
parser.add_argument("-x","--fix", default=0, type=int, choices=range(1, max_labs + 1), metavar='INT[1,%s]' % max_labs, help="Fix N labs")
parser.add_argument("--fixlab", default=0, type=int, choices=range(1, max_labs + 1),  metavar='INT[1,%s]' % max_labs, help="Fix lab N")


args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])

print(bcolors.OKGREEN + "(*) Starting Deployer...\n")
print("(!) IT IS STRONGLY RECOMMENDED TO ONLY RUN THIS IN AN AWS INSTANCE DEDICATED TO THESE LABS")
print("(!) If not run in a clean aws instance then expect issues")
print("(*) Please note we only support up to %s labs..." % max_labs)
print("(*) Deploying to AWS_REGION env var if set, else us-west-2 (also set aws_region in terraform.tfvars to match)")
print(bcolors.ENDC)


args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])

if args.packer:
    packer()
elif args.first:
	firstrun()
elif args.imager:
	imager()
elif args.deploy:
	deployer(args.deploy)
	waitdeploy()
elif args.refresh:
	refresh(args.refresh)
elif args.all:
    firstrun()
    imager()
    deployer(args.all)
    refresh(args.all)
elif args.destroy:
    destroy(args.destroy)
elif args.restartlab:
    restartlab(args.restartlab)
elif args.refreshlab:
    refreshlab(args.refreshlab)
elif args.redeployer:
    redeployer(args.redeployer[0], args.redeployer[1])
elif args.fix:
	fix(args.fix)
elif args.fixlab:
    fixlab(args.fixlab)
elif args.destroylab:
    destroylab(args.destroylab)
elif args.redeploylab:
    redeploylab(args.redeploylab)


#TODO: Deploy single lab, Destroy single lab, redeploy entire workspace
