#!/bin/bash
# Diagnostic script for Guacamole instance connectivity issues

set -e

ENVIRONMENT="${1:-production}"
REGION="${2:-us-east-1}"

echo "=== Guacamole Instance Diagnostics ==="
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo ""

# Get instance details
echo "1. Checking instance status..."
INSTANCE_ID=$(aws ec2 describe-instances \
  --region "$REGION" \
  --filters "Name=tag:Environment,Values=$ENVIRONMENT" "Name=tag:Role,Values=Guacamole" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text)

if [ "$INSTANCE_ID" == "None" ] || [ -z "$INSTANCE_ID" ]; then
  echo "❌ No running Guacamole instance found!"
  echo "   Checking all instances..."
  aws ec2 describe-instances \
    --region "$REGION" \
    --filters "Name=tag:Role,Values=Guacamole" \
    --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress,Tags[?Key==`Environment`].Value|[0]]' \
    --output table
  exit 1
fi

echo "✅ Instance ID: $INSTANCE_ID"

# Get instance details
INSTANCE_INFO=$(aws ec2 describe-instances \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].[State.Name,PublicIpAddress,PrivateIpAddress,SecurityGroups[0].GroupId]' \
  --output text)

read -r STATE PUBLIC_IP PRIVATE_IP SG_ID <<< "$INSTANCE_INFO"

echo "   State: $STATE"
echo "   Public IP: $PUBLIC_IP"
echo "   Private IP: $PRIVATE_IP"
echo "   Security Group: $SG_ID"
echo ""

# Check Elastic IP
echo "2. Checking Elastic IP association..."
EIP_INFO=$(aws ec2 describe-addresses \
  --region "$REGION" \
  --filters "Name=instance-id,Values=$INSTANCE_ID" \
  --query 'Addresses[0].[PublicIp,AssociationId]' \
  --output text)

if [ "$EIP_INFO" != "None" ] && [ -n "$EIP_INFO" ]; then
  read -r EIP ASSOC_ID <<< "$EIP_INFO"
  echo "✅ Elastic IP: $EIP (Association: $ASSOC_ID)"
else
  echo "⚠️  No Elastic IP associated with instance"
fi
echo ""

# Check security group rules
echo "3. Checking security group rules..."
SG_RULES=$(aws ec2 describe-security-group-rules \
  --region "$REGION" \
  --group-ids "$SG_ID" \
  --query 'SecurityGroupRules[?IsEgress==`false`].[IpProtocol,FromPort,ToPort,CidrIpv4]' \
  --output table)

echo "$SG_RULES"
echo ""

# Check if ports are accessible
echo "4. Testing port connectivity..."
if [ -n "$PUBLIC_IP" ] && [ "$PUBLIC_IP" != "None" ]; then
  echo "   Testing port 80..."
  timeout 3 bash -c "cat < /dev/null > /dev/tcp/$PUBLIC_IP/80" 2>/dev/null && echo "   ✅ Port 80 is open" || echo "   ❌ Port 80 is closed or unreachable"
  
  echo "   Testing port 443..."
  timeout 3 bash -c "cat < /dev/null > /dev/tcp/$PUBLIC_IP/443" 2>/dev/null && echo "   ✅ Port 443 is open" || echo "   ❌ Port 443 is closed or unreachable"
  
  echo "   Testing port 22 (SSH)..."
  timeout 3 bash -c "cat < /dev/null > /dev/tcp/$PUBLIC_IP/22" 2>/dev/null && echo "   ✅ Port 22 is open" || echo "   ❌ Port 22 is closed or unreachable"
else
  echo "   ⚠️  No public IP to test"
fi
echo ""

# Check if we can SSH (if key is available)
echo "5. Next steps to check services on the instance:"
echo "   SSH into the instance:"
echo "   ssh -i ~/.ssh/cylynk-lab-keypair ubuntu@$PUBLIC_IP"
echo ""
echo "   Once connected, check services:"
echo "   sudo docker ps"
echo "   sudo systemctl status nginx"
echo "   sudo docker-compose -f /opt/guacamole/docker-compose.yml ps"
echo "   sudo docker-compose -f /opt/guacamole/docker-compose.yml logs"
echo ""

echo "=== Summary ==="
if [ "$STATE" == "running" ]; then
  echo "✅ Instance is running"
else
  echo "❌ Instance state: $STATE"
fi

if [ -n "$PUBLIC_IP" ] && [ "$PUBLIC_IP" != "None" ]; then
  echo "✅ Public IP: $PUBLIC_IP"
else
  echo "❌ No public IP assigned"
fi

echo ""
echo "If ports are closed, check:"
echo "1. Security group rules are correct"
echo "2. Instance is in a public subnet"
echo "3. Route table allows internet traffic"
echo "4. Network ACLs allow traffic"
