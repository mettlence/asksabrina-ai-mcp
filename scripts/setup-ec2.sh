#!/bin/bash
set -e

echo "🔧 Setting up EC2 instance for deployment..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
echo "🐳 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed"
else
    echo "✅ Docker Compose already installed"
fi

# Install additional tools
echo "🛠️ Installing additional tools..."
sudo apt install -y git htop curl wget unzip

# Setup firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
echo "✅ Firewall configured"

# Create application directory
echo "📁 Creating application directory..."
sudo mkdir -p /opt/demographics-api
sudo chown -R $USER:$USER /opt/demographics-api
echo "✅ Directory created at /opt/demographics-api"

echo ""
echo "✨ EC2 setup completed successfully!"
echo ""
echo "⚠️  IMPORTANT: You need to logout and login again for Docker permissions to take effect"
echo ""
echo "Next steps:"
echo "1. Logout: exit"
echo "2. Login again: ssh -i your-key.pem ubuntu@your-ec2-ip"
echo "3. Clone your repository to /opt/demographics-api"
echo "4. Run deployment"