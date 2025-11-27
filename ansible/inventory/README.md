# Ansible Inventory Configuration

## Overview

This directory contains both static and dynamic inventory configurations for managing CyberLab infrastructure.

## Inventory Files

### Static Inventory

- **hosts.yml**: Manual inventory for Guacamole and specific AttackBox instances
- **hosts.yml.example**: Template for creating custom static inventory

### Dynamic Inventory

- **aws_ec2.yml**: AWS EC2 dynamic inventory plugin configuration

## Using Dynamic Inventory

### Prerequisites

1. **Install boto3 and botocore** (AWS SDK for Python):

```bash
pip install boto3 botocore
```

2. **Configure AWS credentials** (one of these methods):

   **Option A: AWS CLI credentials file** (~/.aws/credentials):

   ```ini
   [default]
   aws_access_key_id = YOUR_ACCESS_KEY
   aws_secret_access_key = YOUR_SECRET_KEY
   ```

   **Option B: Environment variables**:

   ```bash
   export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY"
   export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

   **Option C: IAM role** (if running from EC2 instance)

3. **Update aws_ec2.yml**:
   - Set correct `regions`
   - Update `ansible_ssh_private_key_file` path
   - Adjust filters if needed

### Testing Dynamic Inventory

List all discovered instances:

```bash
ansible-inventory -i inventory/aws_ec2.yml --list
```

List instances in graph format:

```bash
ansible-inventory -i inventory/aws_ec2.yml --graph
```

Test connectivity to all AttackBox instances:

```bash
ansible all -i inventory/aws_ec2.yml -m ping
```

Test connectivity to specific group (e.g., dev environment):

```bash
ansible env_dev -i inventory/aws_ec2.yml -m ping
```

### Running Playbooks with Dynamic Inventory

Run AttackBox playbook against all instances:

```bash
ansible-playbook -i inventory/aws_ec2.yml playbooks/attackbox.yml
```

Run against specific environment:

```bash
ansible-playbook -i inventory/aws_ec2.yml playbooks/attackbox.yml --limit env_dev
```

Run against specific role:

```bash
ansible-playbook -i inventory/aws_ec2.yml playbooks/attackbox.yml --limit role_AttackBox
```

## Dynamic Inventory Groups

The `aws_ec2.yml` configuration automatically creates these groups:

- **env\_[environment]**: Instances grouped by Environment tag (e.g., `env_dev`, `env_prod`)
- **project\_[name]**: Instances grouped by Project tag (e.g., `project_cyberlab`)
- **role\_[role]**: Instances grouped by Role tag (e.g., `role_AttackBox`)
- **instance*type*[type]**: Instances grouped by type (e.g., `instance_type_t3_medium`)
- **az\_[zone]**: Instances grouped by availability zone

## Hybrid Approach (Static + Dynamic)

You can use both inventories together:

```bash
ansible-playbook -i inventory/hosts.yml -i inventory/aws_ec2.yml playbooks/site.yml
```

This allows you to:

- Manage Guacamole with static inventory
- Auto-discover AttackBox instances with dynamic inventory

## Troubleshooting

### No instances found

1. Check AWS credentials are configured
2. Verify filters in `aws_ec2.yml` match your tags
3. Ensure instances are running
4. Check region is correct

### Connection issues

1. Verify security groups allow SSH from your IP
2. Check SSH key path in `aws_ec2.yml`
3. Ensure `ansible_user` is correct (kali or ubuntu)

### Boto3 errors

```bash
pip install --upgrade boto3 botocore
```

## Best Practices

1. **Use tags consistently** in Terraform to ensure instances are discovered
2. **Cache inventory** for better performance (already enabled in aws_ec2.yml)
3. **Limit playbook runs** to specific groups when testing
4. **Use --check mode** before making changes:
   ```bash
   ansible-playbook -i inventory/aws_ec2.yml playbooks/attackbox.yml --check
   ```

## References

- [Ansible AWS EC2 Inventory Plugin](https://docs.ansible.com/ansible/latest/collections/amazon/aws/aws_ec2_inventory.html)
- [Ansible Dynamic Inventory](https://docs.ansible.com/ansible/latest/user_guide/intro_dynamic_inventory.html)
