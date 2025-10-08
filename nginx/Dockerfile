FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config (will be mounted via docker-compose)
# Nginx will look for configs in /etc/nginx/conf.d/

# Create directory for SSL certificates
RUN mkdir -p /etc/nginx/ssl

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]