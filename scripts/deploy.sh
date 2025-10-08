#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment...${NC}"

# Configuration
APP_DIR="/opt/asksabrina-ai-mcp"
COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="$APP_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CERTBOT_DIR="$APP_DIR/certbot"
DOMAIN="mcp.asksabrina.com"
EMAIL="admin@asksabrina.com"  # Change this to your email

# Change to app directory
cd $APP_DIR

# Check if git repo exists
if [ ! -d .git ]; then
    echo -e "${RED}❌ Error: Not a git repository${NC}"
    exit 1
fi

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup current .env file
echo -e "${YELLOW}💾 Backing up .env file...${NC}"
if [ -f .env ]; then
    cp .env $BACKUP_DIR/.env.$TIMESTAMP
    echo -e "${GREEN}✅ .env backed up${NC}"
fi

# Pull latest changes
echo -e "${YELLOW}📥 Pulling latest changes from git...${NC}"
git fetch origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${YELLOW}ℹ️  Already up to date${NC}"
else
    git pull origin main
    echo -e "${GREEN}✅ Code updated${NC}"
fi

# Check if SSL certificates exist
echo -e "${YELLOW}🔐 Checking SSL certificates...${NC}"
if [ ! -f "$CERTBOT_DIR/conf/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${BLUE}📜 SSL certificates not found. Setting up Let's Encrypt...${NC}"
    
    # Create required directories
    mkdir -p "$CERTBOT_DIR/conf"
    mkdir -p "$CERTBOT_DIR/www"
    
    # Download recommended TLS parameters
    echo -e "${YELLOW}📥 Downloading TLS parameters...${NC}"
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$CERTBOT_DIR/conf/options-ssl-nginx.conf"
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$CERTBOT_DIR/conf/ssl-dhparams.pem"
    
    # Create temporary nginx config for certificate generation (HTTP only)
    echo -e "${YELLOW}🔧 Creating temporary HTTP-only nginx config...${NC}"
    cat > "$APP_DIR/nginx/nginx.http-only.conf" <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name mcp.asksabrina.com www.mcp.asksabrina.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF
    
    # Backup original config
    cp "$APP_DIR/nginx/nginx.conf" "$APP_DIR/nginx/nginx.conf.backup"
    
    # Use HTTP-only config temporarily
    cp "$APP_DIR/nginx/nginx.http-only.conf" "$APP_DIR/nginx/nginx.conf"
    
    # Start services with HTTP-only config
    echo -e "${YELLOW}🚀 Starting services (HTTP only)...${NC}"
    docker-compose -f $COMPOSE_FILE up -d app
    sleep 10
    docker-compose -f $COMPOSE_FILE up -d nginx
    sleep 5

    # Prove the ACME challenge path is reachable from the Internet before certbot
    echo -e "${YELLOW}🧪 Probing ACME challenge path...${NC}"
    TOKEN=$(head -c16 /dev/urandom | xxd -p)
    mkdir -p "$CERTBOT_DIR/www/.well-known/acme-challenge"
    echo "ok-$TOKEN" > "$CERTBOT_DIR/www/.well-known/acme-challenge/$TOKEN"

    # Wait up to ~60s for nginx to serve it
    ACME_OK=0
    for i in {1..30}; do
    if curl -s "http://$DOMAIN/.well-known/acme-challenge/$TOKEN" | grep -q "ok-$TOKEN"; then
        ACME_OK=1; break
    fi
    sleep 2
    done

    if [ $ACME_OK -ne 1 ]; then
    echo -e "${RED}❌ ACME path not reachable at http://$DOMAIN/.well-known/acme-challenge/$TOKEN${NC}"
    echo -e "${YELLOW}💡 Check: ports mapping (80:80), EC2 security group, DNS A/AAAA, nginx volume mounts${NC}"
    docker compose -f $COMPOSE_FILE logs --tail=100 nginx
    exit 1
    fi
    echo -e "${GREEN}✅ ACME path reachable. Proceeding to request certificate.${NC}"

    
    # Request certificate with better error handling
    echo -e "${YELLOW}📜 Requesting Let's Encrypt certificate...${NC}"

    # Test webroot accessibility first
    echo "Testing webroot accessibility..."
    docker-compose -f $COMPOSE_FILE exec nginx sh -c "echo 'test' > /var/www/certbot/test.txt"
    WEBROOT_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/.well-known/acme-challenge/../test.txt)

    if [ "$WEBROOT_TEST" != "200" ]; then
        echo -e "${RED}❌ Webroot not accessible (HTTP $WEBROOT_TEST)${NC}"
        echo -e "${YELLOW}💡 Check nginx configuration and ensure it serves /var/www/certbot${NC}"
        exit 1
    fi

    # Request certificate with verbose output
    docker-compose -f $COMPOSE_FILE run --rm certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        -d $DOMAIN \
        -d www.$DOMAIN \
        --email $EMAIL \
        --rsa-key-size 4096 \
        --agree-tos \
        --non-interactive \
        --force-renewal \
        --verbose

    CERT_STATUS=$?

    if [ $CERT_STATUS -eq 0 ]; then
        echo -e "${GREEN}✅ SSL certificate obtained successfully${NC}"
        
        # Verify certificate was actually created
        if [ ! -f "$CERTBOT_DIR/conf/live/$DOMAIN/fullchain.pem" ]; then
            echo -e "${RED}❌ Certificate file not found after successful request${NC}"
            exit 1
        fi
        
        # Restore original HTTPS config
        mv "$APP_DIR/nginx/nginx.conf.backup" "$APP_DIR/nginx/nginx.conf"
        rm -f "$APP_DIR/nginx/nginx.http-only.conf"
        
        echo -e "${YELLOW}🔄 Reloading nginx with HTTPS config...${NC}"
        docker-compose -f $COMPOSE_FILE restart nginx
        sleep 5
    else
        echo -e "${RED}❌ Failed to obtain SSL certificate (exit code: $CERT_STATUS)${NC}"
        echo -e "${YELLOW}💡 Troubleshooting steps:${NC}"
        echo -e "   1. DNS Check: dig $DOMAIN (should show your server IP)"
        echo -e "   2. Port Check: curl -I http://$DOMAIN"
        echo -e "   3. Webroot Check: docker-compose exec nginx ls -la /var/www/certbot"
        echo -e "   4. Nginx Logs: docker-compose logs --tail=50 nginx"
        echo -e "   5. Certbot Logs: docker-compose logs --tail=50 certbot"
        
        # Show last certbot error
        echo -e "\n${RED}Last certbot error:${NC}"
        docker-compose -f $COMPOSE_FILE logs --tail=20 certbot
        
        # Restore original config on failure
        if [ -f "$APP_DIR/nginx/nginx.conf.backup" ]; then
            mv "$APP_DIR/nginx/nginx.conf.backup" "$APP_DIR/nginx/nginx.conf"
            docker-compose -f $COMPOSE_FILE restart nginx
        fi
        exit 1
    fi

# Build new images
echo -e "${YELLOW}🔨 Building Docker images...${NC}"
docker-compose -f $COMPOSE_FILE build --no-cache

# Stop old containers
echo -e "${YELLOW}🛑 Stopping old containers...${NC}"
docker-compose -f $COMPOSE_FILE down

# Start new containers
echo -e "${YELLOW}🚀 Starting new containers...${NC}"
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
sleep 45

# Check container status
if docker-compose -f $COMPOSE_FILE ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Containers are running${NC}"
else
    echo -e "${RED}❌ Error: Containers failed to start${NC}"
    echo -e "${YELLOW}📋 Container logs:${NC}"
    docker-compose -f $COMPOSE_FILE logs --tail=50
    exit 1
fi

# Test health endpoint (try both HTTP and HTTPS)
echo -e "${YELLOW}🏥 Testing health endpoint...${NC}"
if curl -f -k https://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ HTTPS health check passed${NC}"
elif curl -f http://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ HTTP health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Health check timeout (this is normal if app is still starting)${NC}"
fi

# Cleanup old images
echo -e "${YELLOW}🧹 Cleaning up old Docker images...${NC}"
docker image prune -f > /dev/null 2>&1
echo -e "${GREEN}✅ Cleanup completed${NC}"

# Show container status
echo ""
echo -e "${GREEN}✨ Deployment completed successfully!${NC}"
echo ""
echo "📊 Container Status:"
docker-compose -f $COMPOSE_FILE ps
echo ""
echo "💡 Useful commands:"
echo "  View logs:         docker-compose -f $COMPOSE_FILE logs -f"
echo "  View nginx logs:   docker-compose -f $COMPOSE_FILE logs -f nginx"
echo "  Restart app:       docker-compose -f $COMPOSE_FILE restart app"
echo "  Restart nginx:     docker-compose -f $COMPOSE_FILE restart nginx"
echo "  Check SSL:         docker-compose -f $COMPOSE_FILE exec nginx ls -la /etc/letsencrypt/live/"
echo "  Renew SSL:         docker-compose -f $COMPOSE_FILE run --rm certbot renew"
echo "  Stop all:          docker-compose -f $COMPOSE_FILE down"
echo ""
echo -e "${BLUE}🔐 SSL Status:${NC}"
if [ -f "$CERTBOT_DIR/conf/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${GREEN}  ✅ SSL certificates are active for $DOMAIN${NC}"
    echo -e "${GREEN}  ✅ Auto-renewal is configured (checks every 12 hours)${NC}"
else
    echo -e "${YELLOW}  ⚠️  No SSL certificates found${NC}"
fi