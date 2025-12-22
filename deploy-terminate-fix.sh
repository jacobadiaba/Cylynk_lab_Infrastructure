#!/bin/bash
# Quick deploy script for terminate-session fix
# This only updates the environment variable, no need to rebuild Lambda

set -e

echo "🚀 Deploying Guacamole public IP fix..."
echo ""

cd environments/dev

echo "📋 Current configuration:"
terraform output -json | grep -A 3 guacamole || echo "No Guacamole outputs found"
echo ""

echo "🔄 Applying Terraform changes (environment variables only)..."
terraform apply -target=module.orchestrator.aws_lambda_function.terminate_session -auto-approve

echo ""
echo "✅ Deploy complete!"
echo ""
echo "The terminate-session Lambda now uses:"
echo "  1. GUACAMOLE_API_URL (if set)"
echo "  2. GUACAMOLE_PUBLIC_IP (for Lambdas outside VPC)"
echo "  3. GUACAMOLE_PRIVATE_IP (for Lambdas in VPC)"
echo ""
echo "Test by clicking 'End Session' in Moodle - should complete in ~2 seconds"
