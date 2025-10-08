#!/bin/bash

set -e

echo "🚀 Starting deployment..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Pull latest changes (if using git)
if [ -d .git ]; then
    echo "📥 Pulling latest changes..."
    git pull origin main
fi

# Backup current state
echo "💾 Creating backup..."
./scripts/backup.sh

# Build and deploy
echo "🔨 Building containers..."
docker-compose -f docker-compose.prod.yml build --no-cache

echo "🔄 Stopping old containers..."
docker-compose -f docker-compose.prod.yml down

echo "🚀 Starting new containers..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for health check
echo "⏳ Waiting for health check..."
sleep 10

# Verify deployment
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ Deployment successful!"
else
    echo "❌ Deployment failed! Rolling back..."
    docker-compose -f docker-compose.prod.yml down
    # Restore from backup logic here
    exit 1
fi

# Cleanup old images
echo "🧹 Cleaning up old images..."
docker image prune -f

echo "✨ Deployment completed successfully!"