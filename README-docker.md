# Docker Setup for Growatt API

This document provides instructions for setting up the Growatt API using Docker and Docker Compose with Prometheus monitoring.

## Prerequisites

- Docker and Docker Compose installed on your system
- SSL certificates for your domain

## Quick Start

1. Make sure you have your SSL certificates in the `nginx/ssl/` directory:

   - `growatt-api.crt` - Your SSL certificate
   - `growatt-api.key` - Your SSL private key

2. Build and start the containers:

```bash
docker-compose up -d
```

This will start:

- The Growatt API Flask application
- Nginx as a reverse proxy
- Prometheus for monitoring
- Grafana for visualization (optional)

## Accessing the Services

- Growatt API: https://your-domain
- Prometheus: http://your-domain:9090
- Grafana: http://your-domain:3000 (default login: admin/admin)

## Configuration

### Environment Variables

You can modify environment variables in the `docker-compose.yml` file:

```yaml
environment:
  - SECRET_KEY=change_this_to_a_random_secret_string
  - DEBUG=False
```

### Prometheus Configuration

Prometheus configuration is stored in `prometheus/prometheus.yml`. You can modify it to add more targets or change scraping intervals.

### Nginx Configuration

The Nginx configuration is in `nginx/growatt-api.conf`. Update the `server_name` directive with your actual domain.

## Monitoring

This setup includes Prometheus for monitoring and Grafana for visualization. Metrics from the Flask application are exposed at the `/metrics` endpoint.

### Setting up Grafana

1. Access Grafana at http://your-domain:3000
2. Log in with default credentials (admin/admin)
3. Add Prometheus as a data source:
   - URL: http://prometheus:9090
4. Import a dashboard or create your own to visualize metrics

## Troubleshooting

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs growatt-api
docker-compose logs nginx
docker-compose logs prometheus
```

### Restart Services

```bash
docker-compose restart growatt-api
```

### Rebuild the Application

```bash
docker-compose down
docker-compose up --build -d
```
