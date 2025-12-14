#!/bin/bash
#
# Oracle Cloud VM Setup Script
# Run this script ONCE on a fresh Ubuntu VM to prepare it for Mail Agent deployment
#
# Usage: bash setup-vm.sh [staging|production]
#

set -e

ENV=${1:-staging}

echo "=================================================="
echo "  Mail Agent - Oracle Cloud VM Setup"
echo "  Environment: $ENV"
echo "=================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running as ubuntu user
if [ "$USER" != "ubuntu" ]; then
    print_error "This script must be run as ubuntu user"
    exit 1
fi

print_status "Starting VM setup for $ENV environment..."

# 1. System Update
echo ""
print_status "Step 1/9: Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# 2. Install Docker
echo ""
print_status "Step 2/9: Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_status "Docker installed successfully"
else
    print_status "Docker already installed"
fi

# 3. Install Docker Compose
echo ""
print_status "Step 3/9: Installing Docker Compose..."
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# Verify installation
docker --version
docker compose version

# 4. Install additional tools
echo ""
print_status "Step 4/9: Installing additional tools..."
sudo apt-get install -y \
    git \
    curl \
    wget \
    vim \
    htop \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban

# 5. Configure Firewall (UFW)
echo ""
print_status "Step 5/9: Configuring firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8000/tcp    # Backend API
sudo ufw allow 3000/tcp    # Grafana (optional)
sudo ufw allow 5555/tcp    # Flower (optional)
sudo ufw allow 9090/tcp    # Prometheus (optional)
sudo ufw --force enable

print_status "Firewall configured"
sudo ufw status

# 6. Configure Fail2ban (SSH protection)
echo ""
print_status "Step 6/9: Configuring Fail2ban..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 7. Create directory structure
echo ""
print_status "Step 7/9: Creating directory structure..."
mkdir -p ~/Mail-Agent
mkdir -p ~/backups
mkdir -p ~/logs

# 8. Clone repository (if not exists)
echo ""
print_status "Step 8/9: Setting up Git repository..."
if [ ! -d "~/Mail-Agent/.git" ]; then
    cd ~
    git clone https://github.com/1987-Dmytro/Mail-Agent.git
    cd Mail-Agent

    if [ "$ENV" == "staging" ]; then
        git checkout develop
    else
        git checkout main
    fi

    print_status "Repository cloned"
else
    print_status "Repository already exists"
fi

# 9. Setup log rotation
echo ""
print_status "Step 9/9: Configuring log rotation..."
sudo tee /etc/logrotate.d/mailagent > /dev/null <<EOF
/home/ubuntu/Mail-Agent/backend/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
    postrotate
        docker compose -f /home/ubuntu/Mail-Agent/backend/docker-compose.yml restart app > /dev/null 2>&1 || true
    endscript
}
EOF

print_status "Log rotation configured"

# Print summary
echo ""
echo "=================================================="
echo -e "${GREEN}  VM Setup Complete! 🎉${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Log out and log back in to apply Docker group membership"
echo "     → ssh -i your-key ubuntu@$HOSTNAME"
echo ""
echo "  2. Configure GitHub secrets in your repository:"
echo "     → ${ENV^^}_VM_IP: $(curl -s ifconfig.me)"
echo "     → ORACLE_SSH_PRIVATE_KEY: your SSH private key"
echo ""
echo "  3. Setup Nginx with SSL (optional):"
echo "     → bash ~/Mail-Agent/backend/scripts/setup-nginx.sh $ENV yourdomain.com"
echo ""
echo "  4. Deploy from GitHub Actions or manually:"
echo "     → Push to develop (staging) or main (production)"
echo ""
echo "System Information:"
echo "  - Hostname: $HOSTNAME"
echo "  - Public IP: $(curl -s ifconfig.me)"
echo "  - Docker: $(docker --version)"
echo "  - Docker Compose: $(docker compose version)"
echo ""
print_warning "IMPORTANT: You MUST log out and log back in for Docker permissions to take effect!"
echo ""
