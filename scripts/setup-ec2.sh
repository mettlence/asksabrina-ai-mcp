#!/bin/bash

set -e

echo "🔧 Setting up EC2 instance..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install additional tools
sudo apt install -y git htop curl wget unzip fail2ban

# Setup firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Setup fail2ban (protection against brute force)
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Create application directory
mkdir -p ~/app/{certbot/conf,certbot/www,nginx,app,scripts}

# Setup log rotation
sudo tee /etc/logrotate.d/docker-containers <<EOF
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    missingok
    delaycompress
    copytruncate
}
EOF

echo "✅ EC2 setup completed!"
echo "⚠️  Please log out and log back in for Docker permissions to take effect"