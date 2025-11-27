#!/bin/bash
# packer/attackbox/scripts/setup-rdp.sh
# Configure RDP (xrdp) server for remote desktop access

# Don't use set -e to avoid stopping on non-critical errors
exec > >(tee /tmp/setup-rdp.log)
exec 2>&1

echo "=========================================="
echo "Setting up RDP Server (xrdp)"
echo "Started: $(date)"
echo "=========================================="

export DEBIAN_FRONTEND=noninteractive

# Detect username
if id "kali" &>/dev/null; then
    USERNAME="kali"
    USERHOME="/home/kali"
elif id "ubuntu" &>/dev/null; then
    USERNAME="ubuntu"
    USERHOME="/home/ubuntu"
else
    echo "Error: Cannot determine username"
    exit 1
fi

echo "Configuring RDP for user: $USERNAME"

# Install xrdp and dependencies
echo "======================================"
echo "[1/5] Installing xrdp server..."
echo "======================================"
sudo apt-get update
sudo apt-get install -y \
    xrdp \
    xorgxrdp \
    xfce4 \
    xfce4-goodies \
    dbus-x11 \
    x11-xserver-utils || { echo "Warning: Some RDP packages failed to install"; }

# Configure xrdp to use XFCE
echo "======================================"
echo "[2/5] Configuring xrdp for XFCE..."
echo "======================================"

# Use provided password or generate random one
if [ -n "$RDP_PASSWORD" ]; then
    echo "Using provided RDP password"
else
    RDP_PASSWORD=$(openssl rand -base64 12 | tr -d '=+/' | cut -c1-12)
    echo "Generated random RDP password"
fi
echo "$USERNAME:$RDP_PASSWORD" | sudo chpasswd

# Unlock the account (Kali AMI has accounts locked by default)
sudo passwd -u $USERNAME
echo "Account unlocked for RDP access"

# Save password for retrieval
sudo mkdir -p /opt/cyberlab
echo "$RDP_PASSWORD" | sudo tee /opt/cyberlab/rdp-password.txt > /dev/null
sudo chmod 600 /opt/cyberlab/rdp-password.txt

echo "RDP Password: $RDP_PASSWORD"
echo "Password saved to: /opt/cyberlab/rdp-password.txt"

sudo -u $USERNAME tee $USERHOME/.xsession > /dev/null <<'XSESSION'
#!/bin/bash
export XDG_SESSION_DESKTOP=xfce
export XDG_CURRENT_DESKTOP=XFCE
exec startxfce4
XSESSION

sudo chmod +x $USERHOME/.xsession

# Configure xrdp
echo "======================================"
echo "[3/5] Configuring xrdp settings..."
echo "======================================"
sudo tee /etc/xrdp/startwm.sh > /dev/null <<'STARTWM'
#!/bin/sh
# xrdp X session start script

if [ -r /etc/default/locale ]; then
  . /etc/default/locale
  export LANG LANGUAGE
fi

# Execute session start script
if [ -x "$HOME/.xsession" ]; then
    exec $HOME/.xsession
else
    exec startxfce4
fi
STARTWM

sudo chmod +x /etc/xrdp/startwm.sh

# Configure xrdp.ini for better performance
sudo sed -i 's/max_bpp=32/max_bpp=24/' /etc/xrdp/xrdp.ini
sudo sed -i 's/#tcp_nodelay=true/tcp_nodelay=true/' /etc/xrdp/xrdp.ini

# Add xrdp user to ssl-cert group
sudo adduser xrdp ssl-cert

# Enable xrdp service
echo "======================================"
echo "[4/5] Enabling xrdp service..."
echo "======================================"
sudo systemctl enable xrdp
sudo systemctl enable xrdp-sesman

# Configure firewall (if ufw is installed)
if command -v ufw >/dev/null 2>&1; then
    echo "Configuring firewall for RDP..."
    sudo ufw allow 3389/tcp comment 'RDP' || true
fi

# Create RDP information file
echo "======================================"
echo "[5/5] Creating RDP information file..."
echo "======================================"
sudo mkdir -p /opt/cyberlab
sudo tee /opt/cyberlab/rdp-info.txt > /dev/null <<INFO
RDP Server Configuration
========================

Port: 3389
Protocol: RDP (Remote Desktop Protocol)
Desktop Environment: XFCE4

Connection Details:
  Address: <instance-ip>:3389
  Username: $USERNAME
  Password: $RDP_PASSWORD

Management Commands:
  Status:  sudo systemctl status xrdp
  Restart: sudo systemctl restart xrdp
  Stop:    sudo systemctl stop xrdp
  Start:   sudo systemctl start xrdp

Logs:
  XRDP:    journalctl -u xrdp -f
  Session: journalctl -u xrdp-sesman -f
  User:    tail -f ~/.xsession-errors

Performance Tuning:
  - Using 24-bit color depth for better performance
  - TCP_NODELAY enabled for lower latency
  - XFCE4 lightweight desktop environment

Troubleshooting:
  - Check xrdp status: sudo systemctl status xrdp
  - View logs: sudo journalctl -u xrdp -n 50
  - Test connection: nc -zv localhost 3389
  - Restart services: sudo systemctl restart xrdp xrdp-sesman

Connecting from:
  Windows:  Use built-in Remote Desktop Connection (mstsc.exe)
  macOS:    Use Microsoft Remote Desktop from App Store
  Linux:    Use remmina or xfreerdp

Example xfreerdp command:
  xfreerdp /v:<instance-ip> /u:$USERNAME /p:<password> /cert:ignore /size:1920x1080
INFO

sudo chmod 644 /opt/cyberlab/rdp-info.txt

# Create helper scripts
sudo tee /usr/local/bin/rdp-status > /dev/null <<'RDPSTATUS'
#!/bin/bash
echo "=== RDP Server Status ==="
echo ""
sudo systemctl status xrdp --no-pager
echo ""
echo "=== RDP Session Manager Status ==="
sudo systemctl status xrdp-sesman --no-pager
echo ""
echo "=== Listening Ports ==="
sudo ss -tlnp | grep 3389
echo ""
echo "=== Recent Logs ==="
sudo journalctl -u xrdp -n 10 --no-pager
RDPSTATUS

sudo chmod +x /usr/local/bin/rdp-status

echo ""
echo "=========================================="
echo "RDP Server Setup Complete!"
echo "=========================================="
echo ""
echo "RDP Details:"
echo "  Port: 3389"
echo "  Username: $USERNAME"
echo "  Desktop: XFCE4"
echo ""
echo "Management commands:"
echo "  rdp-status - Show RDP status and logs"
echo ""
echo "Info saved to: /opt/cyberlab/rdp-info.txt"
echo ""
echo "Note: RDP will auto-start on boot"
echo "=========================================="

exit 0