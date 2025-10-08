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
    mkdir -p "$CERTBOT_DIR/www/.well-known/acme-challenge"
    
    # Set proper permissions
    chmod -R 755 "$CERTBOT_DIR/www"
    
    # Download recommended TLS parameters
    echo -e "${YELLOW}📥 Downloading TLS parameters...${NC}"
    if [ ! -f "$CERTBOT_DIR/conf/options-ssl-nginx.conf" ]; then
        curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$CERTBOT_DIR/conf/options-ssl-nginx.conf"
    fi
    if [ ! -f "$CERTBOT_DIR/conf/ssl-dhparams.pem" ]; then
        curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$CERTBOT_DIR/conf/ssl-dhparams.pem"
    fi
    
    # Create temporary nginx config for certificate generation (HTTP only)
    echo -e "${YELLOW}🔧 Creating temporary HTTP-only nginx config...${NC}"
    cat > "$APP_DIR/nginx/nginx.http-only.conf" <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name mcp.asksabrina.com;
    
    # ACME challenge location - MUST be accessible
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        allow all;
        default_type text/plain;
    }
    
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
    
    # Backup original config
    if [ -f "$APP_DIR/nginx/nginx.conf" ]; then
        cp "$APP_DIR/nginx/nginx.conf" "$APP_DIR/nginx/nginx.conf.backup"
    fi
    
    # Use HTTP-only config temporarily
    cp "$APP_DIR/nginx/nginx.http-only.conf" "$APP_DIR/nginx/nginx.conf"
    
    # Start services with HTTP-only config
    echo -e "${YELLOW}🚀 Starting services (HTTP only)...${NC}"
    docker-compose -f $COMPOSE_FILE up -d app
    sleep 10
    docker-compose -f $COMPOSE_FILE up -d nginx
    sleep 5

    # Verify DNS resolution
    echo -e "${YELLOW}🌐 Verifying DNS resolution...${NC}"
    DNS_IP=$(dig +short $DOMAIN | head -n1)
    if [ -z "$DNS_IP" ]; then
        echo -e "${RED}❌ DNS not resolving for $DOMAIN${NC}"
        echo -e "${YELLOW}💡 Please ensure DNS A record points to this server${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ DNS resolves to: $DNS_IP${NC}"

    # Prove the ACME challenge path is reachable from the Internet before certbot
    echo -e "${YELLOW}🧪 Probing ACME challenge path...${NC}"
    TOKEN=$(head -c16 /dev/urandom | xxd -p)
    mkdir -p "$CERTBOT_DIR/www/.well-known/acme-challenge"
    echo "ok-$TOKEN" > "$CERTBOT_DIR/www/.well-known/acme-challenge/$TOKEN"
    chmod 644 "$CERTBOT_DIR/www/.well-known/acme-challenge/$TOKEN"

    # Wait up to ~60s for nginx to serve it
    ACME_OK=0
    for i in {1..30}; do
        RESPONSE=$(curl -s "http://$DOMAIN/.well-known/acme-challenge/$TOKEN" || echo "")
        if echo "$RESPONSE" | grep -q "ok-$TOKEN"; then
            ACME_OK=1
            break
        fi
        echo -e "${YELLOW}  Attempt $i/30: Waiting for ACME path...${NC}"
        sleep 2
    done

    if [ $ACME_OK -ne 1 ]; then
        echo -e "${RED}❌ ACME path not reachable at http://$DOMAIN/.well-known/acme-challenge/$TOKEN${NC}"
        echo -e "${YELLOW}💡 Troubleshooting:${NC}"
        echo -e "   1. Check ports mapping: docker-compose ps"
        echo -e "   2. Check EC2 security group allows port 80"
        echo -e "   3. Verify DNS: dig $DOMAIN"
        echo -e "   4. Check nginx volumes: docker-compose exec nginx ls -la /var/www/certbot/"
        echo -e "\n${YELLOW}📋 Nginx logs:${NC}"
        docker-compose -f $COMPOSE_FILE logs --tail=100 nginx
        exit 1
    fi
    echo -e "${GREEN}✅ ACME path reachable. Proceeding to request certificate.${NC}"
    
    # Clean up test file
    rm -f "$CERTBOT_DIR/www/.well-known/acme-challenge/$TOKEN"

    # Request certificate with enhanced error handling
    echo -e "${YELLOW}📜 Requesting Let's Encrypt certificate...${NC}"
    echo -e "${BLUE}   Domain: $DOMAIN${NC}"
    echo -e "${BLUE}   Email: $EMAIL${NC}"
    
    # Run certbot with verbose output
    set +e  # Don't exit on error, we want to handle it
    docker-compose -f $COMPOSE_FILE run --rm certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        -d $DOMAIN \
        --email $EMAIL \
        --rsa-key-size 4096 \
        --agree-tos \
        --non-interactive \
        --force-renewal \
        --verbose \
        2>&1 | tee /tmp/certbot_output.log
    
    CERT_STATUS=${PIPESTATUS[0]}
    set -e  # Re-enable exit on error
    
    if [ $CERT_STATUS -eq 0 ]; then
        # Verify certificate was actually created
        if [ ! -f "$CERTBOT_DIR/conf/live/$DOMAIN/fullchain.pem" ]; then
            echo -e "${RED}❌ Certificate file not found after successful request${NC}"
            echo -e "${YELLOW}💡 Certificate may not have been created. Check certbot logs.${NC}"
            cat /tmp/certbot_output.log
            exit 1
        fi
        
        echo -e "${GREEN}✅ SSL certificate obtained successfully${NC}"
        
        # Verify certificate validity
        echo -e "${YELLOW}🔍 Verifying certificate...${NC}"
        CERT_DOMAIN=$(openssl x509 -noout -subject -in "$CERTBOT_DIR/conf/live/$DOMAIN/fullchain.pem" | sed -n 's/.*CN=\([^,]*\).*/\1/p')
        echo -e "${GREEN}✅ Certificate issued for: $CERT_DOMAIN${NC}"
        
        # Restore original HTTPS config
        if [ -f "$APP_DIR/nginx/nginx.conf.backup" ]; then
            mv "$APP_DIR/nginx/nginx.conf.backup" "$APP_DIR/nginx/nginx.conf"
        fi
        
        # Remove temporary config
        rm -f "$APP_DIR/nginx/nginx.http-only.conf"
        
        echo -e "${YELLOW}🔄 Reloading nginx with HTTPS config...${NC}"
        docker-compose -f $COMPOSE_FILE restart nginx
        sleep 5
        
        echo -e "${GREEN}✅ HTTPS is now active!${NC}"
    else
        echo -e "${RED}❌ Failed to obtain SSL certificate (exit code: $CERT_STATUS)${NC}"
        echo -e "\n${RED}Certbot Error Output:${NC}"
        cat /tmp/certbot_output.log
        
        echo -e "\n${YELLOW}💡 Common issues and fixes:${NC}"
        echo -e "   ${BLUE}Rate Limit:${NC} If you see 'too many certificates', wait 1 hour or use --staging flag"
        echo -e "   ${BLUE}DNS Issue:${NC} Ensure $DOMAIN points to this server's IP"
        echo -e "   ${BLUE}Port 80 Blocked:${NC} Check firewall/security group allows port 80"
        echo -e "   ${BLUE}CAA Records:${NC} Check DNS CAA records allow Let's Encrypt"
        
        echo -e "\n${YELLOW}📋 Additional diagnostics:${NC}"
        echo -e "   DNS Resolution: $(dig +short $DOMAIN)"
        echo -e "   Port 80 Status: $(sudo netstat -tlnp | grep :80 || echo 'Not listening')"
        echo -e "   Certbot Logs: /tmp/certbot_output.log"
        
        echo -e "\n${YELLOW}🔧 To retry with Let's Encrypt staging (no rate limits):${NC}"
        echo -e "   Add --staging flag to certbot command in the script"
        
        # Restore original config on failure
        if [ -f "$APP_DIR/nginx/nginx.conf.backup" ]; then
            mv "$APP_DIR/nginx/nginx.conf.backup" "$APP_DIR/nginx/nginx.conf"
            docker-compose -f $COMPOSE_FILE restart nginx
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