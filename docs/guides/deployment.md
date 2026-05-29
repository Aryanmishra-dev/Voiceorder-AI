# Deployment Guide

Docker assets live under `deployment/docker`.

```bash
cp config/.env.example config/.env.development
docker compose -f deployment/docker/docker-compose.yml up --build
```

For production, provide real secrets through your deployment environment or a private env file based on `config/.env.production`.
