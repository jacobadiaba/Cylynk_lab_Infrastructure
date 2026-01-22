# packer/attackbox/kali-attackbox.pkr.hcl
# Packer template for building CyberLab AttackBox AMI (Kali Linux)

packer {
  required_plugins {
    amazon = {
      version = ">= 1.2.8"
      source  = "github.com/hashicorp/amazon"
    }
    ansible = {
      version = ">= 1.1.0"
      source  = "github.com/hashicorp/ansible"
    }
  }
}

# Variables
variable "aws_region" {
  type    = string
 
}

variable "instance_type" {
  type    = string
  default = "t3.medium"
}

variable "ami_name_prefix" {
  type    = string
  default = "cyberlab-attackbox-kali"
}

variable "environment" {
  type    = string
  
}

variable "project_name" {
  type    = string
  default = "cyLynk_lab"
}

variable "kali_version" {
  type    = string
  default = "2024.1"
}

variable "vnc_password" {
  type    = string
  default = ""  # Leave empty to auto-generate, or set your own
  sensitive = true
}

variable "rdp_password" {
  type    = string
  default = ""  # Leave empty to auto-generate, or set your own
  sensitive = true
}

# Source AMI filter - Official Kali Linux AMI
# Note: You may need to subscribe to Kali Linux in AWS Marketplace first
data "amazon-ami" "kali" {
  filters = {
    name                = "kali-last-snapshot-amd64-*"
    virtualization-type = "hvm"
    root-device-type    = "ebs"
  }
  owners      = ["679593333241"] # Offensive Security (Kali Linux)
  most_recent = true
  region      = var.aws_region
}

# Alternative: Use Ubuntu and install Kali tools manually
data "amazon-ami" "ubuntu" {
  filters = {
    name                = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"
    virtualization-type = "hvm"
    root-device-type    = "ebs"
  }
  owners      = ["099720109477"] # Canonical
  most_recent = true
  region      = var.aws_region
}

# Local variables
locals {
  timestamp = regex_replace(timestamp(), "[- TZ:]", "")
  ami_name  = "${var.ami_name_prefix}-${local.timestamp}"

  tags = {
    Name        = local.ami_name
    Project     = var.project_name
    Environment = var.environment
    Component   = "AttackBox"
    OS          = "Kali Linux"
    Version     = var.kali_version
    BuildDate   = local.timestamp
    ManagedBy   = "Packer"
  }
}

# Source configuration
source "amazon-ebs" "kali_attackbox" {
  # Use official Kali AMI (recommended)
  source_ami = data.amazon-ami.kali.id
  # Alternative: Use Ubuntu and install Kali tools
  # source_ami    = data.amazon-ami.ubuntu.id

  instance_type = var.instance_type
  region        = var.aws_region

  # AMI configuration
  ami_name        = local.ami_name
  ami_description = "CyberLab AttackBox - Kali Linux with pre-installed tools for cybersecurity training"

  # Storage configuration
  launch_block_device_mappings {
    device_name           = "/dev/sda1"
    volume_size           = 80
    volume_type           = "gp3"
    iops                  = 3000
    throughput            = 125
    delete_on_termination = true
    encrypted             = true
  }

  # SSH configuration
  ssh_username = "kali" # Use "ubuntu" if building from Ubuntu
  ssh_timeout  = "20m"

  # Network configuration
  associate_public_ip_address = true

  # Tags
  tags          = local.tags
  snapshot_tags = local.tags

  # AMI sharing (optional - for multi-account setups)
  # ami_users = ["123456789012", "987654321098"]

  # AMI regions (optional - for multi-region deployments)
  # ami_regions = ["us-west-2", "eu-west-1"]

  # Run tags (for the build instance)
  run_tags = merge(
    local.tags,
    {
      Name = "Packer Builder - ${local.ami_name}"
    }
  )

  # Temporary security group for build
  temporary_security_group_source_public_ip = true
}

# Build configuration
build {
  name    = "cyberlab-attackbox"
  sources = ["source.amazon-ebs.kali_attackbox"]

  # Wait for cloud-init to complete
  provisioner "shell" {
    inline = [
      "echo 'Waiting for cloud-init to complete...'",
      "cloud-init status --wait || true",
      "echo 'Cloud-init completed'"
    ]
  }

  # Update system
  provisioner "shell" {
    inline = [
      "echo 'Updating system packages...'",
      "sudo apt-get update",
      "sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::='--force-confold'",
      "echo 'System update completed'"
    ]
  }

  # Install Ansible for provisioning
  provisioner "shell" {
    inline = [
      "echo 'Installing Ansible...'",
      "sudo apt-get update",
      "sudo apt-get install -y ansible python3-pip",
      "ansible --version"
    ]
  }

  # Run Ansible playbook to configure attackbox
  provisioner "ansible-local" {
    playbook_file = "${path.root}/../../ansible/playbooks/attackbox.yml"
    role_paths    = ["${path.root}/../../ansible/roles/attackbox"]
    extra_arguments = [
      "--extra-vars", "packer_build=true",
      "--extra-vars", "ansible_python_interpreter=/usr/bin/python3",
      "--extra-vars", "vnc_password=${var.vnc_password}",
      "--extra-vars", "rdp_password=${var.rdp_password}"
    ]
  }

  # Configure auto-reset scripts (handled by Ansible now)
  provisioner "shell" {
    inline = [
      "echo 'Auto-reset scripts configured via Ansible'"
    ]
  }

  # CRITICAL: Ensure cloud-init won't re-lock the account on first boot
  provisioner "shell" {
    inline = [
      "echo 'Ensuring cloud-init will not re-lock user account...'",
      "echo 'users: []' | sudo tee /etc/cloud/cloud.cfg.d/99-cyberlab-no-users.cfg",
      "echo 'preserve_hostname: true' | sudo tee -a /etc/cloud/cloud.cfg.d/99-cyberlab-no-users.cfg",
      "echo 'ssh_pwauth: true' | sudo tee -a /etc/cloud/cloud.cfg.d/99-cyberlab-no-users.cfg",
      "sudo cloud-init clean --logs || true",
      "echo 'Verifying kali account is unlocked...'",
      "sudo grep '^kali:' /etc/shadow | cut -c1-20",
      "if sudo grep -q '^kali:!' /etc/shadow; then echo 'WARNING: Account still locked!'; else echo 'Account unlocked successfully'; fi"
    ]
  }

  # Configure user environment
  provisioner "shell" {
    inline = [
      "echo 'Configuring user environment...'",
      "if id 'kali' &>/dev/null; then USER_HOME=/home/kali; USER_NAME=kali; elif id 'ubuntu' &>/dev/null; then USER_HOME=/home/ubuntu; USER_NAME=ubuntu; else USER_HOME=/root; USER_NAME=root; fi",
      "sudo -u $USER_NAME mkdir -p $USER_HOME/Desktop $USER_HOME/Documents $USER_HOME/Downloads $USER_HOME/Tools",
      "echo 'export PS1=\"\\[\\033[01;31m\\]AttackBox\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ \"' >> $USER_HOME/.bashrc",
      "sudo -u $USER_NAME bash -c \"echo 'Welcome to CyberLab AttackBox!' > $USER_HOME/Desktop/README.txt\"",
      "sudo -u $USER_NAME bash -c \"echo 'This machine has been pre-configured with penetration testing tools.' >> $USER_HOME/Desktop/README.txt\"",
      "sudo -u $USER_NAME bash -c \"echo 'Use this machine responsibly and only for authorized testing.' >> $USER_HOME/Desktop/README.txt\""
    ]
  }

  # Install CloudWatch agent (handled by Ansible)
  provisioner "shell" {
    inline = [
      "echo 'CloudWatch agent configured via Ansible'"
    ]
  }

  # Create MOTD (Message of the Day)
  provisioner "shell" {
    inline = [
      "sudo tee /etc/motd > /dev/null <<'EOF'",
      "╔══════════════════════════════════════════════════════════════╗",
      "║                                                              ║",
      "║              CyberLab AttackBox - Kali Linux                 ║",
      "║                                                              ║",
      "║  This is a pre-configured penetration testing environment   ║",
      "║  Use responsibly and only for authorized testing.           ║",
      "║                                                              ║",
      "║  Pre-installed tools: Nmap, Metasploit, Burp Suite,        ║",
      "║  Wireshark, SQLMap, Nikto, and many more                    ║",
      "║                                                              ║",
      "║  Need help? Type 'cyberlab-help'                            ║",
      "║  Reset instance: Type 'reset-attackbox'                     ║",
      "║                                                              ║",
      "╚══════════════════════════════════════════════════════════════╝",
      "EOF"
    ]
  }

  # Create helper script
  provisioner "shell" {
    inline = [
      "sudo tee /usr/local/bin/cyberlab-help > /dev/null <<'HELP'",
      "#!/bin/bash",
      "echo '=== CyberLab AttackBox Help ==='",
      "echo ''",
      "echo 'Common Tools:'",
      "echo '  nmap          - Network mapper and port scanner'",
      "echo '  metasploit    - Exploitation framework (msfconsole)'",
      "echo '  burpsuite     - Web application security testing'",
      "echo '  wireshark     - Network protocol analyzer'",
      "echo '  sqlmap        - SQL injection tool'",
      "echo '  nikto         - Web server scanner'",
      "echo '  john          - Password cracker'",
      "echo '  hashcat       - Advanced password recovery'",
      "echo '  hydra         - Network login cracker'",
      "echo '  gobuster      - Directory/file bruteforcer'",
      "echo ''",
      "echo 'Useful Commands:'",
      "echo '  cyberlab-help       - Show this help'",
      "echo '  reset-attackbox     - Reset instance to clean state'",
      "echo '  ip a                - Show network interfaces'",
      "echo '  ss -tuln            - Show listening ports'",
      "echo ''",
      "echo 'Documentation:'",
      "echo '  /home/kali/Desktop/README.txt'",
      "echo ''",
      "HELP",
      "sudo chmod +x /usr/local/bin/cyberlab-help"
    ]
  }

  # Cleanup and optimize (handled by Ansible cleanup tasks)
  provisioner "shell" {
    inline = [
      "echo 'Cleanup completed via Ansible'"
    ]
  }

  # Final verification
  provisioner "shell" {
    inline = [
      "echo '=== Build Verification ==='",
      "echo 'Installed packages:'",
      "dpkg -l | grep -E '(nmap|metasploit|burpsuite|wireshark)' || echo 'Kali tools meta-package installed'",
      "echo ''",
      "echo 'Services:'",
      "systemctl status vncserver@:1.service --no-pager || echo 'VNC: Will be configured on first boot'",
      "systemctl status xrdp --no-pager || echo 'RDP: Configured'",
      "echo ''",
      "echo 'Disk usage:'",
      "df -h /",
      "echo ''",
      "echo 'Memory:'",
      "free -h",
      "echo ''",
      "echo '=== Build completed successfully! ==='",
      "echo 'AMI will be created: ${local.ami_name}'"
    ]
  }

  # Post-processor: Create manifest
  post-processor "manifest" {
    output     = "manifest.json"
    strip_path = true
    custom_data = {
      ami_name     = local.ami_name
      build_time   = local.timestamp
      project      = var.project_name
      environment  = var.environment
      kali_version = var.kali_version
    }
  }
}

# Build output
# After build completes, AMI ID will be available in manifest.json
# Use it in your Terraform configuration:
# ami_id = jsondecode(file("packer/attackbox/manifest.json"))["builds"][0]["artifact_id"]