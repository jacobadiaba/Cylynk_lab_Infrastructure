#!/bin/bash
# packer/attackbox/scripts/setup-vnc.sh
# Configure VNC server for remote desktop access

# Don't use set -e to avoid stopping on non-critical errors
exec > >(tee /tmp/setup-vnc.log)
exec 2>&1

echo "=========================================="
echo "Setting up VNC Server"
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

echo "Configuring VNC for user: $USERNAME"

# Install VNC server and desktop environment
echo "======================================"
echo "[1/6] Installing VNC server and XFCE desktop..."
echo "======================================"
sudo apt-get update
sudo apt-get install -y \
    tigervnc-standalone-server \
    tigervnc-common \
    xfce4 \
    xfce4-goodies \
    dbus-x11 \
    x11-xserver-utils \
    xinit || { echo "Warning: Some VNC packages failed to install"; }

# Create VNC directory
echo "======================================"
echo "[2/6] Creating VNC configuration directory..."
echo "======================================"
sudo -u $USERNAME mkdir -p $USERHOME/.vnc

# Set VNC password
echo "======================================"
echo "[3/6] Setting up VNC password..."
echo "======================================"
# Use provided password or generate random one
if [ -n "$VNC_PASSWORD" ]; then
    echo "Using provided VNC password"
else
    VNC_PASSWORD=$(openssl rand -base64 8 | tr -d '=+/' | cut -c1-8)
    echo "Generated random VNC password"
fi
echo "$VNC_PASSWORD" | sudo -u $USERNAME vncpasswd -f > $USERHOME/.vnc/passwd
sudo chmod 600 $USERHOME/.vnc/passwd
sudo chown $USERNAME:$USERNAME $USERHOME/.vnc/passwd

# Save password for retrieval
sudo mkdir -p /opt/cyberlab
echo "$VNC_PASSWORD" | sudo tee /opt/cyberlab/vnc-password.txt > /dev/null
sudo chmod 600 /opt/cyberlab/vnc-password.txt

echo "VNC Password: $VNC_PASSWORD"
echo "Password saved to: /opt/cyberlab/vnc-password.txt"

# Create xstartup file
echo "======================================"
echo "[4/6] Creating VNC startup configuration..."
echo "======================================"
sudo -u $USERNAME tee $USERHOME/.vnc/xstartup > /dev/null <<'XSTARTUP'
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS

[ -r $HOME/.Xresources ] && xrdb $HOME/.Xresources
xsetroot -solid grey
vncconfig -iconic &

# Start basic window manager instead of full session
xfwm4 &
xfce4-panel &
xfdesktop &
exec xfce4-terminal
XSTARTUP

sudo chmod +x $USERHOME/.vnc/xstartup
sudo chown $USERNAME:$USERNAME $USERHOME/.vnc/xstartup

# Create VNC config file
echo "======================================"
echo "[5/6] Creating VNC configuration..."
echo "======================================"
sudo -u $USERNAME tee $USERHOME/.vnc/config > /dev/null <<'VNCCONFIG'
# VNC server configuration
geometry=1920x1080
depth=24
dpi=96
localhost=no
alwaysshared
VNCCONFIG

# Create systemd service for VNC
echo "======================================"
echo "[6/6] Creating VNC systemd service..."
echo "======================================"
sudo tee /etc/systemd/system/vncserver@.service > /dev/null <<VNCSERVICE
[Unit]
Description=Remote desktop service (VNC)
After=syslog.target network.target

[Service]
Type=simple
User=$USERNAME
PAMName=login
PIDFile=$USERHOME/.vnc/%H%i.pid
ExecStartPre=/bin/sh -c '/usr/bin/vncserver -kill :%i > /dev/null 2>&1 || :'
ExecStart=/usr/bin/vncserver :%i -geometry 1920x1080 -depth 24 -localhost no
ExecStop=/usr/bin/vncserver -kill :%i
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
VNCSERVICE

# Reload systemd and enable VNC
sudo systemctl daemon-reload
sudo systemctl enable vncserver@1.service

# Create helper script to start VNC
sudo tee /usr/local/bin/start-vnc > /dev/null <<'STARTVNC'
#!/bin/bash
# Start VNC server
echo "Starting VNC server..."
sudo systemctl start vncserver@1.service

# Wait a moment
sleep 2

# Check status
if sudo systemctl is-active --quiet vncserver@1.service; then
    echo "✓ VNC server started successfully"
    echo ""
    echo "Connect using:"
    echo "  VNC Viewer: $(hostname -I | awk '{print $1}'):5901"
    echo "  Password: See /opt/cyberlab/vnc-password.txt"
else
    echo "✗ VNC server failed to start"
    sudo systemctl status vncserver@1.service
fi
STARTVNC

sudo chmod +x /usr/local/bin/start-vnc

# Create helper script to stop VNC
sudo tee /usr/local/bin/stop-vnc > /dev/null <<'STOPVNC'
#!/bin/bash
# Stop VNC server
echo "Stopping VNC server..."
sudo systemctl stop vncserver@1.service
echo "✓ VNC server stopped"
STOPVNC

sudo chmod +x /usr/local/bin/stop-vnc

# Configure firewall (if ufw is installed)
if command -v ufw >/dev/null 2>&1; then
    echo "Configuring firewall for VNC..."
    sudo ufw allow 5901/tcp comment 'VNC' || true
fi

# Create VNC information file
sudo mkdir -p /opt/cyberlab
sudo tee /opt/cyberlab/vnc-info.txt > /dev/null <<INFO
VNC Server Configuration
========================

Port: 5901
Display: :1
Resolution: 1920x1080
Desktop: XFCE4

Password: $(cat /opt/cyberlab/vnc-password.txt)

Management Commands:
  Start VNC:  start-vnc
  Stop VNC:   stop-vnc
  Status:     sudo systemctl status vncserver@1.service
  Restart:    sudo systemctl restart vncserver@1.service

Manual Commands:
  Start:  vncserver :1 -geometry 1920x1080 -depth 24
  Stop:   vncserver -kill :1
  List:   vncserver -list

Connecting:
  VNC Viewer: <instance-ip>:5901
  Password: (see above)

Troubleshooting:
  View logs: journalctl -u vncserver@1.service -f
  Kill all:  vncserver -kill :*
  Reset:     rm -rf ~/.vnc/*.pid ~/.vnc/*.log
INFO

sudo chmod 644 /opt/cyberlab/vnc-info.txt

echo ""
echo "=========================================="
echo "VNC Server Setup Complete!"
echo "=========================================="
echo ""
echo "VNC Details:"
echo "  Port: 5901"
echo "  Display: :1"
echo "  Password: $VNC_PASSWORD"
echo ""
echo "Management commands:"
echo "  start-vnc  - Start VNC server"
echo "  stop-vnc   - Stop VNC server"
echo ""
echo "Info saved to: /opt/cyberlab/vnc-info.txt"
echo ""
echo "Note: VNC will auto-start on boot"
echo "=========================================="

exit 0