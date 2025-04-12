# Nginx Reverse Proxy Setup for Growatt API

This document provides instructions for setting up an Nginx reverse proxy for the Growatt API Flask application with security best practices.

## Prerequisites

- Nginx installed on your server
- SSL/TLS certificate for your domain
- The Growatt API Flask application running on port 5000

## Installation Steps

1. Copy the Nginx configuration file to the appropriate location:

```bash
sudo cp nginx/growatt-api.conf /etc/nginx/sites-available/
```

2. Create a symbolic link to enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/growatt-api.conf /etc/nginx/sites-enabled/
```

3. Update your domain name in the configuration file:

```bash
sudo nano /etc/nginx/sites-available/growatt-api.conf
```

Replace `growatt-api.example.com` with your actual domain name.

4. Set up SSL certificates:

   - Place your SSL certificate at `/etc/nginx/ssl/growatt-api.crt`
   - Place your private key at `/etc/nginx/ssl/growatt-api.key`

   You can use Let's Encrypt to generate free SSL certificates:

   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d growatt-api.example.com
   ```

5. Test the Nginx configuration:

```bash
sudo nginx -t
```

6. If the test passes, restart Nginx:

```bash
sudo systemctl restart nginx
```

## Security Features

The Nginx configuration includes several security features:

- HTTPS with TLS 1.2/1.3 only
- HTTP Strict Transport Security (HSTS)
- Content Security Policy (CSP)
- X-Content-Type-Options, X-Frame-Options, and X-XSS-Protection headers
- Rate limiting to prevent brute force attacks
- Restriction of access to hidden files
- Buffer size limitations
- Timeout settings to prevent slow attacks

## Running Growatt API with Gunicorn

For production use, it's recommended to run the Flask application with Gunicorn:

1. Install Gunicorn:

```bash
pip install gunicorn
```

2. Run the application with Gunicorn:

```bash
gunicorn -w 4 -b 127.0.0.1:5000 "app:create_app()"
```

You can create a systemd service to manage the Gunicorn process automatically.

## Troubleshooting

- If you can't access your site, check Nginx error logs:

```bash
sudo tail -f /var/log/nginx/error.log
```

- If the proxy can't connect to the Flask app, ensure it's running and listening on the correct port:

```bash
ps aux | grep flask
netstat -tuln | grep 5000
```

## Maintenance

- Regularly update Nginx to patch security vulnerabilities
- Renew SSL certificates before they expire
- Review and update security headers as best practices evolve
