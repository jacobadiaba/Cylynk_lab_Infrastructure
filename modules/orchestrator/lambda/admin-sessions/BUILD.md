# Build Instructions for Admin Dashboard Lambda

## Prerequisites

You need `zip` utility installed. On Windows, you can:

1. Install Git for Windows (includes zip)
2. Install WSL (Windows Subsystem for Linux)
3. Use 7-Zip and rename to .zip

## Option 1: Build on Linux/Mac

```bash
cd modules/orchestrator
bash scripts/build-lambdas.sh
```

This will create `lambda/packages/admin-sessions.zip`.

## Option 2: Manual Build (Windows without zip)

### Using PowerShell:

```powershell
cd modules\orchestrator\lambda\admin-sessions

# Create deployment package
Compress-Archive -Path index.py -DestinationPath ..\packages\admin-sessions.zip -Force
```

### Using Python:

```python
import os
import zipfile

# Create deployment package
lambda_dir = 'modules/orchestrator/lambda/admin-sessions'
output_file = 'modules/orchestrator/lambda/packages/admin-sessions.zip'

with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(f'{lambda_dir}/index.py', 'index.py')

print(f'Created {output_file}')
```

Save as `build_admin_lambda.py` and run:

```bash
python build_admin_lambda.py
```

## Option 3: Build in Docker

```bash
cd modules/orchestrator

docker run --rm -v $(pwd):/workspace -w /workspace python:3.11-alpine sh -c "
  apk add --no-cache zip && \
  cd lambda/admin-sessions && \
  zip -r ../packages/admin-sessions.zip index.py
"
```

## Verification

After building, verify the package:

```bash
# List contents
unzip -l modules/orchestrator/lambda/packages/admin-sessions.zip

# Should show:
# index.py
```

## Deploy to AWS

After building the package, deploy with Terraform:

```bash
cd environments/dev
terraform init
terraform plan
terraform apply
```

The Lambda function will be deployed with the new admin-sessions package.

## Troubleshooting

### Package Too Large

If you see "Deployment package exceeds the size limit":

- Check package size: `ls -lh lambda/packages/admin-sessions.zip`
- Should be < 1MB for this function
- If larger, check for unnecessary files

### Lambda Function Not Updated

If changes don't appear after deployment:

- Terraform uses `source_code_hash` to detect changes
- If you modify `index.py`, rebuild the package
- Run `terraform apply` again

### Import Errors

If Lambda shows "Unable to import module 'index'":

- Verify `index.py` is at the root of the zip
- Check handler is set to `index.lambda_handler`
- Review CloudWatch logs for details

## Next Steps

After building and deploying:

1. Test the endpoint: `GET /admin/sessions`
2. Check CloudWatch logs: `/aws/lambda/cyberlab-dev-admin-sessions`
3. Access admin dashboard in Moodle
4. Verify sessions load correctly

## Quick Build Script (Windows PowerShell)

Save as `build-admin-sessions.ps1`:

```powershell
$source = "modules\orchestrator\lambda\admin-sessions"
$destination = "modules\orchestrator\lambda\packages"

# Create packages directory if it doesn't exist
New-Item -ItemType Directory -Force -Path $destination | Out-Null

# Create zip file
Compress-Archive -Path "$source\index.py" -DestinationPath "$destination\admin-sessions.zip" -Force

Write-Host "✓ Created admin-sessions.zip" -ForegroundColor Green
Write-Host "Size: $((Get-Item "$destination\admin-sessions.zip").Length / 1KB) KB" -ForegroundColor Cyan
```

Run:

```powershell
.\build-admin-sessions.ps1
```
