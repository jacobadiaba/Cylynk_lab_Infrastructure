# GitHub Secrets Setup for Terraform Variables

This project uses GitHub Secrets to manage ALL Terraform variables securely in CI/CD workflows.

## Required GitHub Secrets

Add these secrets to your repository:
**Settings → Secrets and variables → Actions → New repository secret**

### General Configuration (Shared Between Environments)

| Secret Name           | Description                 | Example Dev Value       | Example Prod Value      |
| --------------------- | --------------------------- | ----------------------- | ----------------------- |
| `TF_VAR_PROJECT_NAME` | Project name                | `cyberlab`              | `cyberlab`              |
| `TF_VAR_AWS_REGION`   | AWS region                  | `us-east-1`             | `us-east-1`             |
| `TF_VAR_OWNER`        | Owner/team identifier       | `dev-team@company.com`  | `ops-team@company.com`  |
| `TF_VAR_COST_CENTER`  | Cost center for billing     | `development`           | `education`             |
| `TF_VAR_ALARM_EMAIL`  | Email for CloudWatch alarms | `alerts@yourdomain.com` | `alerts@yourdomain.com` |
| `TF_VAR_ADMIN_EMAIL`  | Admin contact email         | `admin@yourdomain.com`  | `admin@yourdomain.com`  |
| `TF_VAR_VPN_PORT`     | WireGuard VPN port          | `51820`                 | `51820`                 |

### Networking Configuration - Dev Environment

| Secret Name                       | Description           | Example Value   |
| --------------------------------- | --------------------- | --------------- |
| `TF_VAR_VPC_CIDR`                 | VPC CIDR block        | `10.1.0.0/16`   |
| `TF_VAR_MANAGEMENT_SUBNET_CIDR`   | Management subnet     | `10.1.1.0/24`   |
| `TF_VAR_ATTACKBOX_SUBNET_CIDR`    | AttackBox subnet      | `10.1.10.0/24`  |
| `TF_VAR_STUDENT_LABS_CIDR`        | Student labs CIDR     | `10.1.100.0/20` |
| `TF_VAR_STUDENT_LAB_SUBNET_COUNT` | Number of lab subnets | `5`             |
| `TF_VAR_ENABLE_NAT_GATEWAY`       | Enable NAT Gateway    | `true`          |
| `TF_VAR_ENABLE_FLOW_LOGS`         | Enable VPC Flow Logs  | `false`         |
| `TF_VAR_ENABLE_VPC_ENDPOINTS`     | Enable VPC Endpoints  | `false`         |
| `TF_VAR_VPN_SUBNET_CIDR`          | VPN subnet            | `10.51.0.0/16`  |

### Networking Configuration - Prod Environment (with PROD\_ prefix)

| Secret Name                            | Description           | Example Value   |
| -------------------------------------- | --------------------- | --------------- |
| `TF_VAR_PROD_VPC_CIDR`                 | VPC CIDR block        | `10.0.0.0/16`   |
| `TF_VAR_PROD_MANAGEMENT_SUBNET_CIDR`   | Management subnet     | `10.0.1.0/24`   |
| `TF_VAR_PROD_ATTACKBOX_SUBNET_CIDR`    | AttackBox subnet      | `10.0.10.0/24`  |
| `TF_VAR_PROD_STUDENT_LABS_CIDR`        | Student labs CIDR     | `10.0.100.0/20` |
| `TF_VAR_PROD_STUDENT_LAB_SUBNET_COUNT` | Number of lab subnets | `20`            |
| `TF_VAR_PROD_ENABLE_NAT_GATEWAY`       | Enable NAT Gateway    | `true`          |
| `TF_VAR_PROD_ENABLE_FLOW_LOGS`         | Enable VPC Flow Logs  | `true`          |
| `TF_VAR_PROD_ENABLE_VPC_ENDPOINTS`     | Enable VPC Endpoints  | `true`          |
| `TF_VAR_PROD_VPN_SUBNET_CIDR`          | VPN subnet            | `10.50.0.0/16`  |

### Security Configuration

| Secret Name                    | Description          | Example Value     |
| ------------------------------ | -------------------- | ----------------- |
| `TF_VAR_ALLOWED_SSH_CIDR`      | SSH CIDR (dev)       | `YOUR_IP/32`      |
| `TF_VAR_PROD_ALLOWED_SSH_CIDR` | SSH CIDR (prod)      | `YOUR_IP/32`      |
| `TF_VAR_KEY_PAIR_NAME`         | Key pair name (dev)  | `my-dev-keypair`  |
| `TF_VAR_PROD_KEY_PAIR_NAME`    | Key pair name (prod) | `my-prod-keypair` |

### Guacamole Configuration

| Secret Name                           | Description          | Example Value      |
| ------------------------------------- | -------------------- | ------------------ |
| `TF_VAR_GUACAMOLE_INSTANCE_TYPE`      | Instance type (dev)  | `t3.small`         |
| `TF_VAR_PROD_GUACAMOLE_INSTANCE_TYPE` | Instance type (prod) | `t3.medium`        |
| `TF_VAR_GUACAMOLE_DOMAIN_NAME`        | Domain name (dev)    | `""` (empty)       |
| `TF_VAR_PROD_GUACAMOLE_DOMAIN_NAME`   | Domain name (prod)   | `guac.example.com` |
| `TF_VAR_ENABLE_LETS_ENCRYPT`          | Enable SSL (dev)     | `false`            |
| `TF_VAR_PROD_ENABLE_LETS_ENCRYPT`     | Enable SSL (prod)    | `true`             |

### VPN Configuration

| Secret Name                     | Description          | Example Value |
| ------------------------------- | -------------------- | ------------- |
| `TF_VAR_VPN_INSTANCE_TYPE`      | Instance type (dev)  | `t3.micro`    |
| `TF_VAR_PROD_VPN_INSTANCE_TYPE` | Instance type (prod) | `t3.small`    |

### Monitoring Configuration

| Secret Name                                 | Description            | Example Value |
| ------------------------------------------- | ---------------------- | ------------- |
| `TF_VAR_ENABLE_SNS_ALARMS`                  | Enable alarms (dev)    | `false`       |
| `TF_VAR_PROD_ENABLE_SNS_ALARMS`             | Enable alarms (prod)   | `true`        |
| `TF_VAR_LOG_RETENTION_DAYS`                 | Log retention (dev)    | `7`           |
| `TF_VAR_PROD_LOG_RETENTION_DAYS`            | Log retention (prod)   | `30`          |
| `TF_VAR_ENABLE_COST_ANOMALY_DETECTION`      | Cost detection (dev)   | `false`       |
| `TF_VAR_PROD_ENABLE_COST_ANOMALY_DETECTION` | Cost detection (prod)  | `true`        |
| `TF_VAR_COST_ANOMALY_THRESHOLD`             | Alert threshold (dev)  | `50`          |
| `TF_VAR_PROD_COST_ANOMALY_THRESHOLD`        | Alert threshold (prod) | `100`         |

### AWS OIDC Secrets (Already Required)

| Secret Name               | Description                    |
| ------------------------- | ------------------------------ |
| `AWS_ROLE_TO_ASSUME`      | ARN for dev IAM role           |
| `PROD_AWS_ROLE_TO_ASSUME` | ARN for prod IAM role          |
| `AWS_REGION`              | AWS region (e.g., `us-east-1`) |
| `SSH_PRIVATE_KEY`         | For Ansible deployment         |

---

## How It Works

1. **Local Development**: Use `terraform.tfvars` file (gitignored)

   - Copy `terraform.tfvars.example` to `terraform.tfvars`
   - Fill in your values

2. **CI/CD Pipeline**:
   - Workflows create `terraform.tfvars` from GitHub Secrets at runtime
   - File is never committed to repository
   - Secrets are environment-aware (dev vs prod)

## Quick Setup Steps

```bash
# 1. Copy example file for local development
cd environments/dev
cp terraform.tfvars.example terraform.tfvars

# 2. Edit with your values
nano terraform.tfvars  # or your preferred editor

# 3. Verify it's gitignored (should show nothing)
git status terraform.tfvars
```

## Bulk Secret Setup Script

To add all secrets at once, you can use GitHub CLI:

```bash
# Install GitHub CLI if not already: https://cli.github.com/

# Set common values
gh secret set TF_VAR_PROJECT_NAME -b "cyberlab"
gh secret set TF_VAR_AWS_REGION -b "us-east-1"
gh secret set TF_VAR_OWNER -b "your-team@company.com"
gh secret set TF_VAR_COST_CENTER -b "development"
gh secret set TF_VAR_ALARM_EMAIL -b "alerts@yourdomain.com"
gh secret set TF_VAR_ADMIN_EMAIL -b "admin@yourdomain.com"

# Set dev networking
gh secret set TF_VAR_VPC_CIDR -b "10.1.0.0/16"
gh secret set TF_VAR_MANAGEMENT_SUBNET_CIDR -b "10.1.1.0/24"
gh secret set TF_VAR_ATTACKBOX_SUBNET_CIDR -b "10.1.10.0/24"
gh secret set TF_VAR_STUDENT_LABS_CIDR -b "10.1.100.0/20"
gh secret set TF_VAR_STUDENT_LAB_SUBNET_COUNT -b "5"
gh secret set TF_VAR_ENABLE_NAT_GATEWAY -b "true"
gh secret set TF_VAR_ENABLE_FLOW_LOGS -b "false"
gh secret set TF_VAR_ENABLE_VPC_ENDPOINTS -b "false"

# Continue for all other variables...
```

## Security Notes

✅ **DO:**

- Store ALL variables in GitHub Secrets
- Use different values for dev/prod environments
- Restrict `allowed_ssh_cidr` to specific IPs (not `0.0.0.0/0`)
- Keep `terraform.tfvars` in `.gitignore`

❌ **DON'T:**

- Commit `terraform.tfvars` to version control
- Share secret values in chat/email
- Use the same configuration for dev and prod
- Use production key pairs in development

## Environment Differences

The workflows handle environment-specific values:

- **Dev**: Uses `TF_VAR_*` secrets (no prefix)
- **Prod**: Uses `TF_VAR_PROD_*` secrets for environment-specific values

This allows you to have different:

- VPC CIDRs (avoid IP conflicts)
- Instance sizes (smaller in dev, larger in prod)
- Feature flags (disable expensive features in dev)
- SSH access ranges
- Key pairs

## Troubleshooting

**Error: "No value for required variable"**

- Check that all 50+ required secrets are set in GitHub
- Verify secret names match exactly (case-sensitive)
- Boolean values should be `true` or `false` (not quoted)
- Number values should not be quoted

**Error: "Access denied" during Terraform**

- Verify OIDC roles are set up correctly
- Check `AWS_ROLE_TO_ASSUME` secret contains full ARN

**Local Terraform works but GitHub Actions fails**

- Ensure you've added all secrets to GitHub
- Check workflow logs for which variable is missing
- Verify boolean/number formatting (no quotes in secrets)
