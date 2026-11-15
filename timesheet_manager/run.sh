#!/usr/bin/with-contenv bashio
mkdir -p /data
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8099