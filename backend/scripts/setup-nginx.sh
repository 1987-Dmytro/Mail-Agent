#!/bin/bash
#
# Nginx + SSL Setup Script for Mail Agent
# Configures Nginx as reverse proxy with Let's Encrypt SSL
#
# Usage: bash setup-nginx.sh [staging|production] [domain.com]
# Example: bash setup-nginx.sh staging api-staging.mailagent.com
#

set -e

ENV=${1:-staging}
DOMAIN=${2}

if [ -z "$DOMAIN" ]; then
    echo "Error: Domain name is required"
    echo "Usage: bash setup-nginx.sh [staging|production] [domain.com]"
    echo "Example: bash setup-nginx.sh staging api-staging.mailagent.com"
    exit 1
fi

echo "=================================================="
echo "  Nginx + SSL Setup"
echo "  Environment: $ENV"
echo "  Domain: $DOMAIN"
echo "=================================================="

# Create Nginx configuration
echo "Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/mailagent-$ENV > /dev/null <<EOF
# Mail Agent API - $ENV environment
# Managed by setup-nginx.sh

upstream backend_$ENV {
    server localhost:8000 max_fails=3 fail_timeout=30s;
}

# HTTP - Redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN;

    # SSL Configuration (will be managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/mailagent-$ENV-access.log;
    error_log /var/log/nginx/mailagent-$ENV-error.log;

    # Proxy settings
    location / {
        proxy_pass http://backend_$ENV;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Health check endpoint (no logging)
    location /health {
        proxy_pass http://backend_$ENV;
        access_log off;
    }

    # Static files (if any)
    location /static {
        alias /home/ubuntu/Mail-Agent/backend/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable site
echo "Enabling Nginx site..."
sudo ln -sf /etc/nginx/sites-available/mailagent-$ENV /etc/nginx/sites-enabled/

# Test Nginx configuration
echo "Testing Nginx configuration..."
sudo nginx -t

# Reload Nginx
echo "Reloading Nginx..."
sudo systemctl reload nginx

# Obtain SSL certificate with Certbot
echo ""
echo "Obtaining SSL certificate from Let's Encrypt..."
echo "Please enter your email address when prompted."
echo ""

sudo certbot --nginx \
    -d $DOMAIN \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email \
    --redirect \
    || {
        echo ""
        echo "Certificate automation failed. Try manual mode:"
        echo "sudo certbot --nginx -d $DOMAIN"
        exit 1
    }

# Setup auto-renewal
echo "Setting up certificate auto-renewal..."
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

echo ""
echo "=================================================="
echo "  Nginx + SSL Setup Complete! 🎉"
echo "=================================================="
echo ""
echo "Your API is now available at:"
echo "  → https://$DOMAIN"
echo ""
echo "Test your setup:"
echo "  → curl https://$DOMAIN/health"
echo ""
echo "Certificate will auto-renew via systemd timer."
echo "Check renewal status: sudo certbot renew --dry-run"
echo ""
