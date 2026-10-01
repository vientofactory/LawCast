#!/bin/bash
set -e

# Docker Container Management Script
# Usage: ./deploy.sh [service-name]
# If no service name is provided, a full rolling update will be performed.

SERVICE=$1

# Align the sidecar's writable mounts to uid 1001 BEFORE it starts: the
# artifacts bind mount is host-owned (root), so the uid-1001 update tick dies
# creating artifacts/.update.lock with PermissionError, and old /cache volumes
# keep the previous image uid. `</dev/null` is mandatory: the deploy workflow
# feeds this script on stdin (`ssh bash -s` heredoc) and `compose run` drains
# that stdin otherwise (run 36860595171 step 5 ended at such a line).
align_semantic_search_ownership() {
    docker compose run --rm --user 0:0 --no-deps --entrypoint chown \
        semantic-search -R 1001:1001 /cache /app/artifacts </dev/null
    echo "[INFO] Aligned /cache and /app/artifacts ownership to uid 1001."
}

if [ "$SERVICE" = "list" ]; then
  echo "[INFO] Services:"
  docker compose config --services
  exit 0
fi


if [ -z "$SERVICE" ]; then
  echo "[INFO] Since the service name is not specified, a full rolling update will be performed."
  SERVICES=$(docker compose config --services)
  for SVC in $SERVICES; do
    echo "[INFO] Rolling service update in progress... ($SVC)"
    if [ "$SVC" = "semantic-search" ]; then
      align_semantic_search_ownership
    fi
    docker compose up -d --build $SVC
  done
else
  echo "[INFO] Rolling update only specific services ($SERVICE)."
  if [ "$SERVICE" = "semantic-search" ]; then
    align_semantic_search_ownership
  fi
  docker compose up -d --build $SERVICE
fi
