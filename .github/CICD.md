# CI/CD Setup Guide

This document describes the GitHub Actions CI/CD pipelines for the Cyberlab Infrastructure project.

## Overview

The CI/CD setup includes three main workflows:

1. **Terraform Validation** - Validates Terraform code on pull requests
2. **Terraform Deploy** - Deploys infrastructure changes to AWS
3. **Ansible Validation** - Validates Ansible playbooks and roles

## Workflows

### 1. Terraform Validation (`terraform-validate.yml`)

**Triggers:**

- Pull requests to `main` or `develop` branches
- Pushes to `main` branch
- Changes to Terraform files (`environments/**`, `modules/**`)

**Jobs:**

- **terraform-fmt**: Checks Terraform code formatting
- **terraform-validate-dev**: Validates dev environment configuration
- **terraform-validate-prod**: Validates prod environment configuration
- **terraform-plan-dev**: Runs `terraform plan` for dev environment (PR only)

**Features:**

- Posts PR comments with validation results
- Checks code formatting with `terraform fmt`
- Validates syntax with `terraform validate`
- Generates plan output for review

### 2. Terraform Deploy (`terraform-deploy.yml`)

**Triggers:**

- Pushes to `main` branch (auto-deploys to dev)
- Manual workflow dispatch (can deploy to dev or prod)

**Jobs:**

- **terraform-deploy-dev**: Deploys to development environment
- **terraform-deploy-prod**: Deploys to production environment (manual only)

**Features:**

- Automatic deployment to dev on main branch push
- Manual deployment with action selection (plan/apply/destroy)
- Environment protection with GitHub environments
- Deployment summaries with Terraform outputs

### 3. Ansible Validation (`ansible-validate.yml`)

**Triggers:**

- Pull requests to `main` or `develop` branches
- Pushes to `main` branch
- Changes to Ansible files (`ansible/**`)

**Jobs:**

- **ansible-lint**: Runs ansible-lint and yamllint
- **ansible-syntax**: Checks playbook syntax

**Features:**

- YAML linting with yamllint
- Ansible best practices check with ansible-lint
- Syntax validation for all playbooks
- PR comments with validation results

## Setup Instructions

### 1. Configure AWS OIDC Authentication

This project uses **OpenID Connect (OIDC)** for secure, credential-free authentication with AWS. See the comprehensive [AWS OIDC Setup Guide](AWS_OIDC_SETUP.md) for detailed instructions.

**Quick Setup:**

1. Create an AWS OIDC Identity Provider pointing to GitHub
2. Create IAM roles for dev and prod with appropriate trust policies
3. Add the following secrets to GitHub (Settings → Secrets and variables → Actions):

#### Required Secrets:

```
AWS_ROLE_TO_ASSUME         # ARN of IAM role for dev (e.g., arn:aws:iam::123456789012:role/github-actions-terraform-dev)
PROD_AWS_ROLE_TO_ASSUME    # ARN of IAM role for prod (e.g., arn:aws:iam::123456789012:role/github-actions-terraform-prod)
AWS_REGION                 # AWS region (e.g., us-east-1)
```

**Benefits of OIDC:**

- ✅ No long-lived AWS credentials stored in GitHub
- ✅ Automatic credential rotation
- ✅ Fine-grained access control with IAM conditions
- ✅ Better security and audit trail

**Note**: If you previously used static credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`), you can safely delete them after setting up OIDC.

### 2. Configure GitHub Environments

Create two environments in your repository settings:

#### Development Environment

- Name: `development`
- Protection rules: Optional (recommended: require reviewers for critical changes)
- Environment secrets: Use repository secrets

#### Production Environment

- Name: `production`
- Protection rules: **Required**
  - Required reviewers: At least 1-2 reviewers
  - Wait timer: Optional (e.g., 5 minutes)
- Environment secrets: Use production-specific secrets

**To create environments:**

1. Go to Settings → Environments
2. Click "New environment"
3. Enter environment name
4. Configure protection rules
5. Save

### 3. Configure Terraform Backend (Recommended)

For production use, configure a remote backend for Terraform state:

**Create `environments/dev/backend.tf`:**

```hcl
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-locks"
  }
}
```

**Create `environments/prod/backend.tf`:**

```hcl
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-locks"
  }
}
```

### 4. Update Terraform Variables

Ensure your `terraform.tfvars` files contain necessary configuration:

```hcl
# environments/dev/terraform.tfvars
project_name = "cyberlab"
aws_region   = "us-east-1"
owner        = "your-team"
cost_center  = "engineering"
# ... other variables
```

## Usage

### For Pull Requests

1. Create a feature branch: `git checkout -b feature/my-change`
2. Make your changes to Terraform or Ansible files
3. Commit and push: `git push origin feature/my-change`
4. Create a pull request
5. GitHub Actions will automatically:
   - Format check your Terraform code
   - Validate Terraform configuration
   - Run `terraform plan` for dev environment
   - Lint Ansible playbooks
   - Post results as PR comments
6. Review the plan output and validation results
7. Address any issues before merging

### For Deployments

#### Automatic Deployment (Dev)

- Merge PR to `main` branch
- GitHub Actions automatically deploys to dev environment

#### Manual Deployment

1. Go to Actions → Terraform Deploy
2. Click "Run workflow"
3. Select:
   - **Environment**: dev or prod
   - **Action**: plan, apply, or destroy
4. Click "Run workflow"
5. Monitor the workflow execution

## Best Practices

### Code Organization

- Keep environment-specific configurations in `environments/{env}/terraform.tfvars`
- Use modules for reusable infrastructure components
- Follow Terraform naming conventions

### Branch Strategy

- `main`: Production-ready code
- `develop`: Development branch (optional)
- `feature/*`: Feature branches
- Use pull requests for all changes

### Terraform Workflow

1. Always run `terraform fmt -recursive` before committing
2. Review plan output carefully before applying
3. Use meaningful commit messages
4. Tag releases for production deployments

### Ansible Workflow

1. Test playbooks locally before committing
2. Use ansible-lint to catch issues early
3. Keep roles modular and reusable
4. Document role variables in README files

## Troubleshooting

### Terraform Init Fails

- Check AWS credentials are correctly set
- Verify backend configuration is correct
- Ensure S3 bucket and DynamoDB table exist

### Terraform Plan Fails

- Review error messages in workflow logs
- Check variable definitions in `terraform.tfvars`
- Verify AWS permissions for required resources

### Ansible Lint Fails

- Review ansible-lint output for specific issues
- Run locally: `ansible-lint playbooks/ roles/`
- Check YAML syntax with: `yamllint .`

### Permission Errors

- Verify GitHub secrets are set correctly
- Check AWS IAM permissions for the user/role
- Ensure environment protection rules are configured

## Security Considerations

1. **Never commit sensitive data** to the repository
2. **Use GitHub Secrets** for all credentials
3. **Enable branch protection** on main branch
4. **Require code reviews** for production changes
5. **Use environment protection** for production deployments
6. **Rotate AWS credentials** regularly
7. **Audit workflow runs** periodically

## Workflow Permissions

The workflows use the following permissions:

- `contents: read` - Read repository contents
- `pull-requests: write` - Comment on pull requests
- `id-token: write` - For OIDC authentication (future enhancement)

## Future Enhancements

Consider these improvements:

1. **OIDC Authentication**: Use GitHub OIDC provider instead of static credentials
2. **Terraform Cloud**: Integrate with Terraform Cloud for state management
3. **Cost Estimation**: Add Infracost for cost analysis
4. **Security Scanning**: Add tfsec, checkov for security scanning
5. **Slack Notifications**: Notify team of deployment results
6. **Automated Testing**: Add integration tests for deployed infrastructure
7. **Drift Detection**: Schedule daily drift detection jobs

## Support

For issues or questions:

- Check workflow logs in GitHub Actions
- Review this documentation
- Contact the infrastructure team

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform GitHub Actions](https://github.com/hashicorp/setup-terraform)
- [Ansible Lint](https://ansible-lint.readthedocs.io/)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)

<!-- Testing CI/CD -->
