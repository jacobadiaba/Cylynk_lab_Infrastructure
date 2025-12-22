# GitHub Copilot Instructions - CyberLab Infrastructure

## Project Overview

This is a **hybrid IaC project** deploying a cloud-based cybersecurity lab environment (CyberLab) on AWS. The stack integrates:
- **Terraform** (infrastructure provisioning): Modular AWS resources with dev/prod environments
- **Ansible** (configuration management): Post-provisioning setup for Guacamole and AttackBox instances
- **Python Lambdas** (orchestration): Session management API connecting Moodle LMS to lab resources
- **Moodle Plugin** (frontend): PHP/JavaScript plugin providing student access to on-demand Kali Linux AttackBoxes via Guacamole RDP gateway
- **Packer** (AMI building): Custom Kali Linux AttackBox images with pre-installed tools

## Architecture

```
Moodle LMS → API Gateway → Lambda Functions → DynamoDB (sessions)
                                           ↓
                              EC2 Auto Scaling (AttackBox pool)
                                           ↓
                              Guacamole (RDP Gateway) → Student Browser
```

**Key Components:**
- `modules/orchestrator`: Lambda-based API for session lifecycle (create/get-status/terminate/pool-manager/admin-sessions)
- `modules/networking`: VPC with management, AttackBox pool, and student lab subnets
- `modules/guacamole`: Apache Guacamole RDP gateway (browser-based access to AttackBoxes)
- `modules/attackbox`: Auto Scaling Group managing Kali Linux instances
- `moodle-plugin/local_attackbox`: PHP plugin with AJAX endpoints and JavaScript launcher UI

## Critical Workflows

### 1. Terraform Development
```bash
# Always format before committing - CI checks this
terraform fmt -recursive

# Development environment workflow
cd environments/dev
terraform init
terraform plan
terraform apply

# Production deployments are manual via GitHub Actions only
```

**Module Dependencies:** Networking → Security → Guacamole/Orchestrator/AttackBox (check `main.tf` output references)

### 2. Lambda Development
```bash
# Build Lambda packages and layers (common utilities)
cd modules/orchestrator/scripts
./build-lambdas.sh

# Output: lambda/packages/*.zip and lambda/layers/common.zip
# Common layer: modules/orchestrator/lambda/common/*.py (shared utilities for all functions)
```

**Lambda Structure:**
- Each function has `index.py` (entry point with `lambda_handler`)
- Common layer (`lambda/common/`) provides: `utils.py`, DynamoDB/EC2/ASG clients, auth verification
- Functions import via `from utils import DynamoDBClient, verify_moodle_request, ...`

### 3. Ansible Configuration
```bash
cd ansible
# Install Galaxy dependencies first
ansible-galaxy collection install -r requirements.yml

# Update inventory with Terraform outputs
terraform output -json | jq -r '.guacamole_public_ip.value'
# Edit inventory/hosts.yml with IP

# Run playbook
ansible-playbook playbooks/guacamole.yml -i inventory/hosts.yml
```

### 4. Packer Image Building
```bash
cd packer/attackbox
packer build -var-file=variables.pkrvars.hcl kali-attackbox.pkr.hcl
# Creates AMI: cyberlab-attackbox-kali-{timestamp}
```

## Project Conventions

### Terraform
- **Tagging:** All resources use `default_tags` provider block (Project, Environment, ManagedBy, Owner)
- **Naming:** `{project_name}-{environment}-{resource_type}` (e.g., `cyberlab-dev-api-gateway`)
- **Environments:** `environments/dev/` and `environments/prod/` reference `modules/` via relative paths (`../../modules/networking`)
- **Variables:** Each module has `variables.tf` with descriptions, types, defaults. Root environments have `terraform.tfvars.example`
- **State:** Backend configured in `environments/*/backend.tf` (S3 + DynamoDB lock)

### Lambda Functions
- **Authentication:** Moodle requests validated via HMAC-SHA256 tokens (shared secret `MOODLE_WEBHOOK_SECRET`)
- **Session Management:** DynamoDB TTL auto-expires sessions after `SESSION_TTL_HOURS` (default: 4 hours)
- **Error Handling:** All functions use `error_response()` and `success_response()` from common layer
- **Multi-tier Plans:** Functions route to different ASGs based on `plan` field (freemium/starter/pro)

### Moodle Plugin
- **File Structure:** `db/hooks.php` registers callbacks, `classes/hook_callbacks.php` injects JS, `ajax/*.php` endpoints
- **AJAX Pattern:** All endpoints require `require_login()`, check capabilities (`local/attackbox:launchattackbox`)
- **Token Generation:** `ajax/get_token.php` creates HMAC-signed JWTs for API authentication
- **UI:** Floating button injected via `amd/src/launcher.js`, styles auto-loaded from `styles.css`

### CI/CD (GitHub Actions)
- **OIDC Auth:** No AWS credentials stored - uses OIDC with role ARNs (`AWS_ROLE_TO_ASSUME`, `PROD_AWS_ROLE_TO_ASSUME`)
- **Auto-deploy:** Merge to `main` → auto-deploys to dev environment
- **Manual Production:** Prod deployments require manual trigger in Actions tab
- **Validation Checks:** PR must pass `terraform fmt`, `terraform validate`, `ansible-lint`

## Key Files to Reference

- **Module outputs:** `modules/*/outputs.tf` - outputs referenced across modules (e.g., `module.networking.vpc_id`)
- **Session schema:** `modules/orchestrator/README.md` - DynamoDB structure, API contracts
- **Common utilities:** `modules/orchestrator/lambda/common/utils.py` - shared Lambda code
- **Admin dashboard:** `ADMIN_DASHBOARD.md` - session management UI architecture
- **Cost estimation:** `PRODUCTION_COST_ESTIMATE.md` - infrastructure costs breakdown

## Integration Points

1. **Moodle ↔ Lambda:** Plugin generates HMAC token → POST to API Gateway → `create-session` Lambda
2. **Lambda ↔ DynamoDB:** Sessions table (student sessions), instance-pool table (available AttackBoxes), usage table (metrics)
3. **Lambda ↔ EC2/ASG:** Auto Scaling API to launch instances, EC2 API for status checks
4. **Lambda ↔ Guacamole:** REST API to create RDP connections (`GuacamoleClient` in common layer)
5. **Terraform → Ansible:** Terraform creates instances → Ansible configures via dynamic inventory (`inventory/aws_ec2.yml`)

## Common Patterns

### Adding a New Lambda Function
1. Create `modules/orchestrator/lambda/{function-name}/index.py` with `lambda_handler(event, context)`
2. Import utilities: `from utils import DynamoDBClient, error_response, success_response`
3. Add to `modules/orchestrator/scripts/build-lambdas.sh` FUNCTIONS array
4. Add resource in `modules/orchestrator/main.tf` (Lambda function + API Gateway route if needed)
5. Run `./build-lambdas.sh` to package

### Adding a New Terraform Module
1. Create `modules/{module-name}/` with `main.tf`, `variables.tf`, `outputs.tf`, `README.md`
2. Define outputs in `outputs.tf` for cross-module references
3. Import module in `environments/dev/main.tf` and `environments/prod/main.tf`
4. Pass dependencies via module inputs (e.g., `vpc_id = module.networking.vpc_id`)

### Modifying Session Behavior
- **TTL/Limits:** Update `SESSION_TTL_HOURS`, `MAX_SESSIONS` environment variables in `modules/orchestrator/main.tf`
- **Session Schema:** Modify DynamoDB operations in `lambda/common/utils.py` and update consuming functions
- **Plan Tiers:** Adjust `DEFAULT_PLAN_LIMITS` in `lambda/common/utils.py`, configure ASG names in orchestrator variables

## Testing Locally

```bash
# Terraform validation (run from environment directory)
cd environments/dev
terraform init
terraform validate
terraform plan

# Ansible syntax check
cd ansible
ansible-playbook playbooks/*.yml --syntax-check
ansible-lint playbooks/ roles/

# Lambda testing (requires AWS credentials)
cd modules/orchestrator/lambda/create-session
python -m pytest tests/  # if tests exist
```

## Troubleshooting

- **Lambda import errors:** Ensure common layer is built (`./build-lambdas.sh`) and attached in Terraform
- **Guacamole connection fails:** Check security group rules (port 8080), verify private IP in Lambda env vars
- **Terraform module not found:** Check relative paths in `source` (should be `../../modules/{name}` from environments)
- **CI/CD OIDC errors:** Verify IAM role trust policy includes GitHub OIDC provider, check role ARN in secrets
- **Moodle plugin not loading:** Clear Moodle cache (`php admin/cli/purge_caches.php`), check `version.php` incremented
