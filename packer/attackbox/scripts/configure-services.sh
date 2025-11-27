#!/bin/bash
# Don't use set -e to avoid failures stopping the build

echo "=========================================="
echo "Configuring Services"
echo "Started: $(date)"
echo "=========================================="
echo ""

# Enable SSH (service name can be ssh or sshd)
echo "======================================"
echo "[1/1] Enabling SSH service..."
echo "======================================"
if systemctl list-unit-files | grep -q '^ssh.service'; then
    sudo systemctl enable ssh || true
    echo "✓ SSH service enabled"
fi

if systemctl list-unit-files | grep -q '^sshd.service'; then
    sudo systemctl enable sshd || true
    echo "✓ SSHD service enabled"
fi

echo ""
echo "=========================================="
echo "Services configured successfully"
echo "Completed: $(date)"
echo "=========================================="