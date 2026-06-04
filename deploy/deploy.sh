#!/bin/bash

set -e

REGION=us-east-2
ACCOUNT_ID=288518841669

BACKEND_IMAGE=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/pipelinepulse/backend:latest
FRONTEND_IMAGE=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/pipelinepulse/frontend:latest

echo "Logging into ECR..."

aws ecr get-login-password \
--region $REGION \
| docker login \
--username AWS \
--password-stdin \
$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

echo "Pulling latest images..."

docker pull $BACKEND_IMAGE
docker pull $FRONTEND_IMAGE

echo "Stopping old containers..."

docker rm -f pline-backend || true
docker rm -f pline-frontend || true

echo "Starting backend..."

docker run -d \
--name pline-backend \
--network pipeline \
-p 5000:5000 \
-e SECRET_KEY="HELLO@123" \
-e DATABASE_URL="postgresql://postgres:urRWXR-bMt9d!*~@pipelinepulse-database-server.cbw06aykw15d.us-east-2.rds.amazonaws.com:5432/postgres" \
$BACKEND_IMAGE

echo "Starting frontend..."

docker run -d \
--name pline-frontend \
--network pipeline \
-e API_BASE="/api" \
-e API_PROXY_PATH="/api" \
-e BACKEND_UPSTREAM="http://pline-backend:5000" \
-e NGINX_PORT="80" \
-e PROXY_READ_TIMEOUT="60s" \
-e STATIC_CACHE_CONTROL="no-store, no-cache, must-revalidate, max-age=0" \
--link pline-backend \
-p 80:80 \
$FRONTEND_IMAGE

echo "Deployment Complete"

