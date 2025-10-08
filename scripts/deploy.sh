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
if [ ! -d "$CERTBOT_DIR/conf/live" ] || [ -z "$(ls -A $CERTBOT_DIR/conf/live 2>/dev/null)" ]; then
    echo -e "${BLUE}📜 SSL certificates not found. Initializing Let's Encrypt...${NC}"
    
    # Source domain from .env or use default
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    DOMAIN=${DOMAIN:-"your-domain.com"}
    EMAIL=${LETSENCRYPT_EMAIL:-"admin@${DOMAIN}"}
    
    echo -e "${YELLOW}Domain: $DOMAIN${NC}"
    echo -e "${YELLOW}Email: $EMAIL${NC}"
    
    # Create required directories
    mkdir -p "$CERTBOT_DIR/conf"
    mkdir -p "$CERTBOT_DIR/www"
    
    # Download recommended TLS parameters
    if [ ! -e "$CERTBOT_DIR/conf/options-ssl-nginx.conf" ]; then
        echo -e "${YELLOW}📥 Downloading TLS parameters...${NC}"
        curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$CERTBOT_DIR/conf/options-ssl-nginx.conf"
        curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$CERTBOT_DIR/conf/ssl-dhparams.pem"
    fi
    
    # Create dummy certificate
    echo -e "${YELLOW}🔑 Creating temporary certificate...${NC}"
    path="/etc/letsencrypt/live/$DOMAIN"
    mkdir -p "$CERTBOT_DIR/conf/live/$DOMAIN"
    
    docker-compose -f $COMPOSE_FILE run --rm --entrypoint "\
      openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
        -keyout '$path/privkey.pem' \
        -out '$path/fullchain.pem' \
        -subj '/CN=localhost'" certbot 2>/dev/null || true
    
    # Start nginx with dummy certificate
    echo -e "${YELLOW}🚀 Starting nginx...${NC}"
    docker-compose -f $COMPOSE_FILE up -d nginx
    sleep 5
    
    # Delete dummy certificate
    echo -e "${YELLOW}🗑️  Removing temporary certificate...${NC}"
    docker-compose -f $COMPOSE_FILE run --rm --entrypoint "\
      rm -Rf /etc/letsencrypt/live/$DOMAIN && \
      rm -Rf /etc/letsencrypt/archive/$DOMAIN && \
      rm -Rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot 2>/dev/null || true
    
    # Request real certificate
    echo -e "${YELLOW}📜 Requesting Let's Encrypt certificate...${NC}"
    docker-compose -f $COMPOSE_FILE run --rm --entrypoint "\
      certbot certonly --webroot -w /var/www/certbot \
        -d $DOMAIN \
        --email $EMAIL \
        --rsa-key-size 4096 \
        --agree-tos \
        --non-interactive \
        --force-renewal" certbot
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ SSL certificate obtained successfully${NC}"
    else
        echo -e "${RED}❌ Failed to obtain SSL certificate${NC}"
        echo -e "${YELLOW}💡 Make sure:${NC}"
        echo -e "   - Domain DNS is pointing to this server"
        echo -e "   - Port 80 is accessible from the internet"
        echo -e "   - Domain is correct in .env file"
        exit 1
    fi
    
    # Reload nginx
    docker-compose -f $COMPOSE_FILE exec nginx nginx -s reload 2>/dev/null || true
else
    echo -e "${GREEN}✅ SSL certificates found${NC}"
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
    echo -e "${RED}❌ Warning: Health check failed${NC}"
    echo -e "${YELLOW}Check logs: docker-compose -f $COMPOSE_FILE logs${NC}"
fi

# Check SSL certificate expiry
if [ -d "$CERTBOT_DIR/conf/live" ] && [ -n "$(ls -A $CERTBOT_DIR/conf/live 2>/dev/null)" ]; then
    echo -e "${YELLOW}🔐 Checking SSL certificate expiry...${NC}"
    CERT_FILE=$(find $CERTBOT_DIR/conf/live -name "fullchain.pem" | head -n 1)
    if [ -f "$CERT_FILE" ]; then
        EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
        echo -e "${GREEN}📅 Certificate expires: $EXPIRY${NC}"
    fi
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
echo "  Restart app:       docker-compose -f $COMPOSE_FILE restart app"
echo "  Restart nginx:     docker-compose -f $COMPOSE_FILE restart nginx"
echo "  Renew SSL cert:    docker-compose -f $COMPOSE_FILE run --rm certbot renew"
echo "  Stop all:          docker-compose -f $COMPOSE_FILE down"
echo ""
echo -e "${BLUE}🔐 SSL Status:${NC}"
if [ -d "$CERTBOT_DIR/conf/live" ] && [ -n "$(ls -A $CERTBOT_DIR/conf/live 2>/dev/null)" ]; then
    echo -e "${GREEN}  ✅ SSL certificates are active${NC}"
else
    echo -e "${YELLOW}  ⚠️  No SSL certificates found${NC}"
fi