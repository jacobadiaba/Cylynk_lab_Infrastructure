#!/bin/bash
set -e

echo "Initializing AttackBox instance..."

# Get instance metadata
INSTANCE_ID=$(ec2-metadata --instance-id | cut -d " " -f 2)
PRIVATE_IP=$(ec2-metadata --local-ipv4 | cut -d " " -f 2)

# Configure CloudWatch agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json

# Start VNC server
sudo systemctl start vncserver@1.service

# Start RDP server
sudo systemctl start xrdp

# Log startup
logger -t attackbox "AttackBox $INSTANCE_ID initialized successfully"

echo "AttackBox initialization complete!"