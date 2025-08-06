# JSON-Lite Docker Setup Guide

## Overview

This Docker solution provides containerized deployments for both JSON-Lite components:
- **OP1 Large**: Manual processor for large JSON files
- **OP2 Lite**: FastAPI service for JSON processing

## Architecture

- Multi-stage builds with python:3.11-slim base
- yajl2_c backend compiled for optimal performance
- Non-root user execution for security
- Shared code properly handled (no symlink issues)
- Health checks and monitoring support

## Quick Start

### Using Make (Recommended)

```bash
# Build all images
make build

# Start all services
make up

# View logs
make logs

# Stop services
make down
```

### Using Docker Compose

```bash
# Build and start all services
docker-compose up --build -d

# Start only OP2 Lite API
docker-compose up op2-lite -d

# Start with monitoring
docker-compose --profile monitoring up -d
```

## Service Endpoints

- **OP2 Lite API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Prometheus** (optional): http://localhost:9090

## Directory Structure

```
json-lite/
├── shared/                 # Shared code (copied into containers)
│   ├── streaming_parser.py
│   └── gpu_guard.py
├── op1_large/             # OP1 Large processor
│   ├── Dockerfile
│   ├── requirements.txt
│   └── manual_processor.py
├── op2_lite/              # OP2 Lite API
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── simple_main.py
├── docker-compose.yml     # Orchestration
├── Makefile              # Convenience commands
└── prometheus.yml        # Monitoring config
```

## Environment Variables

Create a `.env` file in the root directory:

```bash
# OP1 Large
JSON_BACKEND=yajl2_c
OP1_MEMORY_LIMIT=2G
OP1_CPU_LIMIT=2

# OP2 Lite
WORKERS=4
OP2_MEMORY_LIMIT=1G
OP2_CPU_LIMIT=2
PORT=8000

# Monitoring
PROMETHEUS_ENABLED=false
```

## Volume Mounts

### OP1 Large
- `./data:/app/data:ro` - Input data (read-only)
- `./output/op1:/app/output` - Processing output

### OP2 Lite
- `./output/op2:/app/output` - API output

## Make Commands

| Command | Description |
|---------|-------------|
| `make build` | Build all Docker images |
| `make up` | Start all services |
| `make up-op1` | Start only OP1 Large |
| `make up-op2` | Start only OP2 Lite |
| `make down` | Stop and remove containers |
| `make logs` | View all logs |
| `make logs-op1` | View OP1 logs |
| `make logs-op2` | View OP2 logs |
| `make shell-op1` | Open shell in OP1 |
| `make shell-op2` | Open shell in OP2 |
| `make health` | Check service health |
| `make monitoring` | Start with Prometheus |
| `make clean` | Remove all containers/volumes |
| `make rebuild` | Rebuild without cache |

## Development Mode

For development with live code reloading:

```bash
# OP1 Large development
make dev-op1

# OP2 Lite development
make dev-op2
```

## Security Features

- Non-root user (`appuser`, UID 1000)
- Read-only volume mounts where appropriate
- Resource limits enforced
- Health checks for availability monitoring
- Network isolation between services

## Monitoring

### Prometheus Metrics

When monitoring profile is enabled:

```bash
make monitoring
```

Access metrics at:
- Prometheus UI: http://localhost:9090
- OP2 Metrics: http://localhost:8000/metrics

### Available Metrics

- `json_requests_total`: Total JSON upload requests
- `json_process_seconds`: Processing duration histogram
- Standard FastAPI/Uvicorn metrics

## Troubleshooting

### Build Issues

```bash
# Clean rebuild
make rebuild

# Remove all Docker artifacts
make prune
```

### Permission Issues

Ensure output directories exist and have correct permissions:

```bash
mkdir -p output/op1 output/op2
chmod 755 output/op1 output/op2
```

### Memory Issues

Adjust memory limits in docker-compose.yml:

```yaml
deploy:
  resources:
    limits:
      memory: 4G  # Increase as needed
```

### Symlink Resolution

The Dockerfiles handle symlinks by copying actual files:

```dockerfile
# Copies shared files into container
COPY shared/ /app/shared/
RUN cp /app/shared/streaming_parser.py /app/op1_large/json_worker/
```

## Performance Tuning

### OP1 Large

- Adjust `JSON_BACKEND` to `yajl2_c` for best performance
- Increase memory limits for larger files
- Mount input data as read-only for security

### OP2 Lite

- Adjust `WORKERS` based on CPU cores
- Use `--reload` flag for development only
- Enable response compression in production

## Production Deployment

1. Use specific image tags instead of `latest`
2. Enable TLS/SSL termination (nginx/traefik)
3. Configure proper logging aggregation
4. Set up monitoring and alerting
5. Use secrets management for sensitive data
6. Configure automatic restarts and health checks

## Support

For issues specific to Docker setup, check:
- Container logs: `make logs`
- Health status: `make health`
- Resource usage: `docker stats`