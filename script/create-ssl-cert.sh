#!/bin/bash

# Create ssl directory if it doesn't exist
mkdir -p ./nginx/ssl

# Generate a self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./nginx/ssl/growatt-api.key \
  -out ./nginx/ssl/growatt-api.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=growatt.local"

# Set proper permissions
chmod 600 ./nginx/ssl/growatt-api.key
chmod 644 ./nginx/ssl/growatt-api.crt

echo "Self-signed SSL certificate generated successfully."
echo "To enable HTTPS:"
echo "1. Uncomment the SSL-related lines in docker-compose.yml"
echo "2. Uncomment the HTTPS server block in nginx/growatt-api.conf"
echo "3. Restart your containers with 'docker-compose down && docker-compose up -d'"
