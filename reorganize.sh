#!/usr/bin/env bash
set -euo pipefail

mkdir -p app/api/v1 app/core app/db/migrations app/models app/schemas app/services app/middleware app/types
mkdir -p static/css tests/unit/services tests/integration tests/fixtures config deployment/docker deployment/ci
mkdir -p docs/architecture docs/api docs/guides

git mv app/config.py app/core/config.py
git mv app/security.py app/core/security.py
git mv app/logger.py app/core/logging.py
git mv app/database.py app/db/session.py
git mv app/models.py app/models/order.py
git mv app/schemas.py app/schemas/order.py
git mv app/types.py app/types/domain.py
git mv app/bot.py app/services/llm_service.py
git mv app/static/css/dashboard.css static/css/dashboard.css
git mv Dockerfile deployment/docker/Dockerfile
git mv docker-compose.yml deployment/docker/docker-compose.yml
git mv .env.example config/.env.example
git mv .github deployment/ci/.github
git mv tests/test_bot.py tests/unit/services/test_bot_service.py
git mv tests/test_schemas.py tests/unit/test_schemas.py
git mv tests/test_security.py tests/unit/test_security.py
git mv tests/test_main.py tests/integration/test_webhook.py
