#!/bin/bash
set -e

# Docker Container Management Script
# Usage: ./deploy.sh [service-name]
# If no service name is provided, a full rolling update will be performed.

SERVICE=$1

# Align the sidecar's writable mounts for the uid-1001 update tick BEFORE the
# container starts (its first write is creating artifacts/.update.lock, which
# failed with PermissionError on a host-owned mount). The chown/chmod run on
# the HOST: a container-side chown was EPERM-denied on every artifacts bind
# file while the /cache volume chown in the same process succeeded (CI run
# 36892165553), and chmod 0777 keeps the mount writable for uid 1001 however
# the daemon maps that uid. `</dev/null` below is mandatory: the deploy
# workflow feeds this script on stdin (`ssh bash -s` heredoc) and `compose
# run` drains that stdin otherwise (run 36860595171 step 5 ended at such a
# line).
align_semantic_search_ownership() {
    local artifacts="semantic-search/artifacts"
    chown -R 1001:1001 "$artifacts" 2>/dev/null || echo "[WARN] host chown skipped; relying on chmod"
    chmod 0777 "$artifacts"
    if [ -e "$artifacts/.update.lock" ]; then
        chmod 0666 "$artifacts/.update.lock"
    fi
    ls -ld "$artifacts"
    docker compose run --rm --user 0:0 --no-deps --entrypoint chown \
        semantic-search -R 1001:1001 /cache </dev/null
    echo "[INFO] Aligned artifacts mount (host chown/chmod) and /cache for uid 1001."
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
