# AttackBox Ansible Role

This Ansible role configures a Kali Linux-based penetration testing environment (AttackBox) with pre-installed tools and remote access capabilities.

## Features

- **System Updates**: Keeps the system up-to-date with latest security patches
- **Penetration Testing Tools**: Installs comprehensive security tools including:
  - Nmap, Metasploit, Burp Suite
  - Wireshark, SQLMap, Nikto
  - John the Ripper, Hashcat, Hydra
  - Gobuster, FFuf, and many more
- **Remote Access**: Configures both VNC and RDP for remote desktop access
- **CloudWatch Integration**: Sets up AWS CloudWatch agent for monitoring
- **User Environment**: Customizes shell with aliases and helper scripts
- **Auto-reset Script**: Provides instance reset functionality

## Requirements

- Ansible 2.9 or higher
- Target OS: Kali Linux or Ubuntu 22.04+
- Sudo/root access on target system

## Role Variables

Available variables are listed below, along with default values (see `defaults/main.yml`):

```yaml
# User configuration
attackbox_user: "kali" # or "ubuntu"
attackbox_user_home: "/home/kali"

# VNC configuration
vnc_display: 1
vnc_port: 5901
vnc_geometry: "1920x1080"
vnc_depth: 24

# RDP configuration
rdp_port: 3389

# CloudWatch configuration
cloudwatch_namespace: "CyberLab/AttackBox"
cloudwatch_log_group: "/cyberlab/production/attackbox"

# Project configuration
attackbox_environment: production
project_name: cyberlab
```

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Configure AttackBox
  hosts: attackbox
  become: true

  roles:
    - role: attackbox
      vars:
        attackbox_environment: development
        vnc_geometry: "1920x1200"
```

## Packer Integration

This role is designed to work with Packer for AMI creation. Set `packer_build: true` when running in Packer:

```hcl
provisioner "ansible-local" {
  playbook_file = "../../ansible/playbooks/attackbox.yml"
  role_paths    = ["../../ansible/roles/attackbox"]
  extra_arguments = [
    "--extra-vars", "packer_build=true"
  ]
}
```

## Tags

The role supports the following tags for selective execution:

- `tools` - Install penetration testing tools
- `vnc` - Configure VNC server
- `rdp` - Configure RDP server
- `cloudwatch` - Setup CloudWatch agent
- `services` - Configure system services
- `user-environment` - Setup user environment
- `scripts` - Install utility scripts
- `cleanup` - Cleanup for AMI creation (Packer only)

Example usage:

```bash
ansible-playbook playbooks/attackbox.yml --tags "tools,vnc"
```

## Post-Installation

After running this role, the following will be available:

### Helper Scripts

- `cyberlab-help` - Display help information
- `reset-attackbox` - Reset instance to clean state
- `start-vnc` - Start VNC server
- `stop-vnc` - Stop VNC server
- `rdp-status` - Check RDP server status

### Access Information

- VNC password: `/opt/cyberlab/vnc-password.txt`
- RDP password: `/opt/cyberlab/rdp-password.txt`
- VNC info: `/opt/cyberlab/vnc-info.txt`
- RDP info: `/opt/cyberlab/rdp-info.txt`

### Default Credentials

- VNC Port: 5901
- RDP Port: 3389
- User: kali (or ubuntu)

## License

MIT

## Author Information

Created for the CyberLab infrastructure project.
