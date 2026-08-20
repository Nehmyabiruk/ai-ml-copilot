#!/bin/bash
set -e

echo "Waiting for database to be ready..."
sleep 5

echo "Starting server..."
exec gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers 1