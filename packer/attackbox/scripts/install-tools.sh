#!/bin/bash
# packer/attackbox/scripts/install-tools.sh
# Install and configure penetration testing tools for AttackBox

# Don't use set -e since we handle errors per-command
exec > >(tee /tmp/install-tools.log)
exec 2>&1

echo "=========================================="
echo "Installing Penetration Testing Tools"
echo "Started: $(date)"
echo "=========================================="

export DEBIAN_FRONTEND=noninteractive

# Update package lists
echo "======================================"
echo "[1/15] Updating package lists..."
echo "======================================"
sudo apt-get update

# Install essential build tools and dependencies
echo "======================================"
echo "[2/15] Installing build essentials..."
echo "======================================"
sudo apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    tmux \
    htop \
    net-tools \
    dnsutils \
    whois \
    netcat-traditional \
    socat \
    python3 \
    python3-pip \
    python3-venv \
    ruby \
    ruby-dev \
    golang-go \
    default-jdk \
    unzip \
    p7zip-full \
    jq

# Clean up after installation
sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/*

# Install Kali tools (if on Kali)
if grep -qi kali /etc/os-release; then
    echo "======================================"
    echo "[3/15] Installing Kali Linux tools..."
    echo "======================================"
    
    # Update Kali repositories first
    echo "Updating Kali repositories..."
    sudo apt-get update
    
    # Install essential Kali tools individually (more reliable than meta-packages on AWS AMI)
    echo "Installing core penetration testing tools..."
    sudo apt-get install -y \
        nmap \
        metasploit-framework \
        wireshark \
        tshark \
        tcpdump \
        nikto \
        hydra \
        john \
        hashcat \
        sqlmap \
        aircrack-ng \
        burpsuite \
        zaproxy \
        dirb \
        dirbuster \
        enum4linux \
        smbclient \
        smbmap \
        crackmapexec \
        gobuster \
        ffuf \
        wfuzz \
        whatweb \
        wafw00f \
        exploitdb \
        searchsploit \
        responder \
        netcat-traditional \
        socat \
        chisel || echo "Some tools may not be available, continuing..."
    
    # Clean up to save space
    sudo apt-get clean
    sudo rm -rf /var/lib/apt/lists/*
else
    echo "======================================"
    echo "[3/15] Not on Kali, installing individual tools..."
    echo "======================================"
    
    # Install Nmap
    sudo apt-get install -y nmap
    
    # Install Metasploit Framework
    curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > /tmp/msfinstall
    chmod 755 /tmp/msfinstall
    sudo /tmp/msfinstall
    
    # Install other essential tools
    sudo apt-get install -y \
        wireshark \
        tcpdump \
        nikto \
        hydra \
        john \
        hashcat \
        sqlmap \
        aircrack-ng \
        wpscan \
        dirb \
        dirbuster
fi

# Install network analysis tools
echo "======================================"
echo "[4/15] Installing network analysis tools..."
echo "======================================"
sudo apt-get install -y \
    nmap \
    masscan \
    netdiscover \
    arp-scan \
    hping3 \
    traceroute \
    mtr \
    iptables \
    nftables || echo "Some network tools not available, continuing..."

# Install web application testing tools
echo "======================================"
echo "[5/15] Installing web application tools..."
echo "======================================"
sudo apt-get install -y \
    burpsuite \
    zaproxy \
    nikto \
    wpscan \
    sqlmap \
    commix \
    wfuzz || echo "Some web tools not available, continuing..."

# Install password cracking tools
echo "======================================"
echo "[6/15] Installing password tools..."
echo "======================================"
sudo apt-get install -y \
    john \
    hashcat \
    hydra \
    medusa \
    crunch \
    cewl || echo "Some password tools not available, continuing..."

# Install exploitation frameworks
echo "======================================"
echo "[7/15] Configuring exploitation frameworks..."
echo "======================================"
# Metasploit database setup
if command -v msfdb >/dev/null 2>&1; then
    sudo msfdb init || true
fi

# Install post-exploitation tools
echo "======================================"
echo "[8/15] Installing post-exploitation tools..."
echo "======================================"
sudo apt-get install -y \
    powershell \
    enum4linux \
    smbclient \
    samba-common-bin \
    impacket-scripts || echo "Some post-exploitation tools not available, continuing..."

# Install Python tools via pip
echo "======================================"
echo "[9/15] Installing Python security tools..."
echo "======================================"
# Use --break-system-packages for system-wide install (safe in a dedicated VM image)
sudo pip3 install --upgrade pip --break-system-packages || true
sudo pip3 install --break-system-packages \
    impacket \
    pwntools \
    scapy \
    requests \
    beautifulsoup4 \
    paramiko \
    pycryptodome \
    cryptography || echo "Some Python tools failed to install, continuing..."

# Install Go tools
echo "======================================"
echo "[10/15] Installing Go security tools..."
echo "======================================"
# Go tools are already available via apt (gobuster, ffuf)
# Skip manual Go installation to avoid path issues
echo "Go-based tools installed via apt package manager"

# Install reconnaissance tools
echo "======================================"
echo "[11/15] Installing reconnaissance tools..."
echo "======================================"
sudo apt-get install -y \
    recon-ng \
    theharvester \
    whatweb \
    wafw00f \
    sublist3r || echo "Some reconnaissance tools not available, continuing..."

# Install vulnerability scanners
echo "======================================"
echo "[12/15] Installing vulnerability scanners..."
echo "======================================"
sudo apt-get install -y \
    nikto \
    wapiti \
    skipfish || echo "Some vulnerability scanners not available, continuing..."

# Install wireless tools
echo "======================================"
echo "[13/15] Installing wireless tools..."
echo "======================================"
sudo apt-get install -y \
    aircrack-ng \
    reaver \
    bully \
    wifite \
    kismet || echo "Some wireless tools not available, continuing..."

# Install forensics tools
echo "======================================"
echo "[14/15] Installing forensics tools..."
echo "======================================"
sudo apt-get install -y \
    binwalk \
    foremost \
    autopsy \
    volatility3 \
    sleuthkit || echo "Some forensics tools not available, continuing..."

# Install useful utilities
echo "======================================"
echo "[15/15] Installing utilities..."
echo "======================================"
sudo apt-get install -y \
    terminator \
    gedit \
    mousepad \
    firefox-esr \
    chromium \
    keepassxc \
    cherrytree \
    flameshot \
    vlc || echo "Some utilities not available, continuing..."

# Skip Docker installation to save disk space
echo "Skipping Docker installation to conserve disk space..."
echo "Docker can be installed post-deployment if needed."

# Create wordlist directory (but skip large downloads)
echo "Setting up wordlists directory..."
sudo mkdir -p /usr/share/wordlists
echo "Note: SecLists and rockyou can be downloaded post-deployment to save build time and space."

# Create tools directory
echo "Setting up tools directory..."
sudo mkdir -p /opt/tools
sudo chown -R kali:kali /opt/tools 2>/dev/null || sudo chown -R ubuntu:ubuntu /opt/tools

echo "Note: Additional tools can be installed post-deployment to save disk space."

# Create aliases
echo "Creating useful aliases..."
# Detect user and create aliases
if [ -d "/home/kali" ]; then
    TARGET_USER="kali"
    TARGET_HOME="/home/kali"
elif [ -d "/home/ubuntu" ]; then
    TARGET_USER="ubuntu"
    TARGET_HOME="/home/ubuntu"
else
    TARGET_USER="root"
    TARGET_HOME="/root"
fi

cat >> $TARGET_HOME/.bash_aliases <<'ALIASES'
# Network scanning
alias qnmap='nmap -sV -sC -O -p-'
alias quickscan='nmap -sV -sC'

# Web testing
alias dirsearch='gobuster dir -w /usr/share/wordlists/dirb/common.txt -u'

# Python server
alias pyserve='python3 -m http.server 8000'

# IP addresses
alias myip='curl ifconfig.me'
alias localip='ip -4 addr show | grep inet | grep -v 127.0.0.1'

# Tools
alias msf='msfconsole'
alias burp='burpsuite &'

# Docker quick commands
alias dkali='docker run -it --rm kalilinux/kali-rolling /bin/bash'
ALIASES

sudo chown $TARGET_USER:$TARGET_USER $TARGET_HOME/.bash_aliases 2>/dev/null || true

# Clean up
echo "Cleaning up..."
sudo apt-get autoremove -y
sudo apt-get autoclean

# Verify installations
echo ""
echo "=========================================="
echo "Installation Verification"
echo "=========================================="

echo "Checking critical tools..."
command -v nmap >/dev/null 2>&1 && echo "✓ nmap" || echo "✗ nmap"
command -v msfconsole >/dev/null 2>&1 && echo "✓ metasploit" || echo "✗ metasploit"
command -v burpsuite >/dev/null 2>&1 && echo "✓ burpsuite" || echo "✗ burpsuite"
command -v wireshark >/dev/null 2>&1 && echo "✓ wireshark" || echo "✗ wireshark"
command -v sqlmap >/dev/null 2>&1 && echo "✓ sqlmap" || echo "✗ sqlmap"
command -v nikto >/dev/null 2>&1 && echo "✓ nikto" || echo "✗ nikto"
command -v john >/dev/null 2>&1 && echo "✓ john" || echo "✗ john"
command -v hashcat >/dev/null 2>&1 && echo "✓ hashcat" || echo "✗ hashcat"
command -v hydra >/dev/null 2>&1 && echo "✓ hydra" || echo "✗ hydra"
command -v gobuster >/dev/null 2>&1 && echo "✓ gobuster" || echo "✗ gobuster"
command -v docker >/dev/null 2>&1 && echo "✓ docker" || echo "✗ docker"

echo ""
echo "Disk space:"
df -h / | tail -1

echo ""
echo "=========================================="
echo "Tool Installation Complete!"
echo "Completed: $(date)"
echo "=========================================="

exit 0