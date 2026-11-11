#!/bin/sh
set -eu

# Preserve the migration probe's reserved loopback port and foreground lifecycle.
# Keep this image pin aligned with the production docker-compose.yml service.
exec docker run --rm --network host --init redis:8.8.0 redis-server "$@"
