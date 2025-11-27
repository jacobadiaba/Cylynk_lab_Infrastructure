#!/bin/bash
# packer/attackbox/scripts/cleanup.sh
# Cleanup and optimize AMI before creating snapshot

# Don't use set -e to allow cleanup to continue even if some steps fail
exec > >(tee /tmp/cleanup.log)
exec 2>&1

echo "=========================================="
echo "Cleaning up and optimizing AMI"
echo "Started: $(date)"
echo "=========================================="

# Stop services that might have leftover data
echo "======================================"
echo "[1/10] Stopping services..."
echo "======================================"
sudo systemctl stop vncserver@1.service 2>/dev/null || true
sudo systemctl stop xrdp 2>/dev/null || true

# Clean package cache
echo "======================================"
echo "[2/10] Cleaning package cache..."
echo "======================================"
sudo apt-get clean
sudo apt-get autoremove -y
sudo apt-get autoclean

# Remove temporary files
echo "======================================"
echo "[3/10] Removing temporary files..."
echo "======================================"
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*
sudo rm -rf /var/cache/apt/archives/*.deb

# Clean logs
echo "======================================"
echo "[4/10] Cleaning logs..."
echo "======================================"
sudo find /var/log -type f -name "*.log" -exec truncate -s 0 {} \;
sudo find /var/log -type f -name "*.gz" -delete
sudo find /var/log -type f -name "*.1" -delete
sudo find /var/log -type f -name "*.old" -delete
sudo rm -rf /var/log/journal/*

# Clean bash history
echo "======================================"
echo "[5/10] Cleaning shell history..."
echo "======================================"
history -c
cat /dev/null > ~/.bash_history
sudo cat /dev/null > /root/.bash_history 2>/dev/null || true

if [ -d "/home/kali" ]; then
    sudo cat /dev/null > /home/kali/.bash_history
fi

if [ -d "/home/ubuntu" ]; then
    sudo cat /dev/null > /home/ubuntu/.bash_history
fi

# Remove cloud-init artifacts
echo "======================================"
echo "[6/10] Cleaning cloud-init data..."
echo "======================================"
sudo cloud-init clean --logs --seed || true
sudo rm -rf /var/lib/cloud/instances/*
sudo rm -rf /var/lib/cloud/instance

# Remove SSH host keys (will be regenerated on first boot)
echo "======================================"
echo "[7/10] Removing SSH host keys..."
echo "======================================"
sudo rm -f /etc/ssh/ssh_host_*

# Remove machine-id (will be regenerated)
echo "======================================"
echo "[8/10] Cleaning machine ID..."
echo "======================================"
sudo truncate -s 0 /etc/machine-id
sudo rm -f /var/lib/dbus/machine-id

# Clean VNC temporary files
echo "======================================"
echo "[9/10] Cleaning VNC temporary files..."
echo "======================================"
if [ -d "/home/kali/.vnc" ]; then
    sudo rm -f /home/kali/.vnc/*.pid
    sudo rm -f /home/kali/.vnc/*.log
fi

if [ -d "/home/ubuntu/.vnc" ]; then
    sudo rm -f /home/ubuntu/.vnc/*.pid
    sudo rm -f /home/ubuntu/.vnc/*.log
fi

# Zero out free space to improve compression
echo "======================================"
echo "[10/10] Zeroing free space (this may take a while)..."
echo "======================================"
sync
# Skip zeroing on Packer build to save time
# sudo dd if=/dev/zero of=/EMPTY bs=1M || true
# sudo rm -f /EMPTY
# sync

# Final disk usage report
echo ""
echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "Disk Usage:"
df -h /
echo ""
echo "Largest directories:"
sudo du -h --max-depth=1 / 2>/dev/null | sort -rh | head -10
echo ""
echo "Completed: $(date)"
echo "=========================================="

exit 0