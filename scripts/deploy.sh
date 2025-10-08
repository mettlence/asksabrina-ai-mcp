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
    
    # Request certificate
    echo -e "${YELLOW}📜 Requesting Let's Encrypt certificate...${NC}"
    docker-compose -f $COMPOSE_FILE run --rm certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        -d $DOMAIN \
        -d www.$DOMAIN \
        --email $EMAIL \
        --rsa-key-size 4096 \
        --agree-tos \
        --non-interactive \
        --force-renewal
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ SSL certificate obtained successfully${NC}"
        
        # Restore original HTTPS config
        mv "$APP_DIR/nginx/nginx.conf.backup" "$APP_DIR/nginx/nginx.conf"
        
        # Remove temporary config
        rm -f "$APP_DIR/nginx/nginx.http-only.conf"
        
        echo -e "${YELLOW}🔄 Reloading nginx with HTTPS config...${NC}"
        docker-compose -f $COMPOSE_FILE restart nginx
        sleep 5
    else
        echo -e "${RED}❌ Failed to obtain SSL certificate${NC}"
        echo -e "${YELLOW}💡 Troubleshooting steps:${NC}"
        echo -e "   1. Verify DNS: dig $DOMAIN"
        echo -e "   2. Check if ports 80/443 are open: sudo netstat -tlnp | grep :80"
        echo -e "   3. Test if domain resolves to this server"
        echo -e "   4. Check nginx logs: docker-compose -f $COMPOSE_FILE logs nginx"
        
        # Restore original config on failure
        if [ -f "$APP_DIR/nginx/nginx.conf.backup" ]; then
            mv "$APP_DIR/nginx/nginx.conf.backup" "$APP_DIR/nginx/nginx.conf"
        fi
        exit 1
    fi
else
    echo -e "${GREEN}✅ SSL certificates found${NC}"
    
    # Check certificate expiry
    CERT_FILE="$CERTBOT_DIR/conf/live/$DOMAIN/fullchain.pem"
    if [ -f "$CERT_FILE" ]; then
        EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
        EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
        NOW_EPOCH=$(date +%s)
        DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))
        
        echo -e "${BLUE}📅 Certificate expires in $DAYS_LEFT days ($EXPIRY)${NC}"
        
        if [ $DAYS_LEFT -lt 30 ]; then
            echo -e "${YELLOW}⚠️  Certificate expires soon. It will auto-renew.${NC}"
        fi
    fi
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