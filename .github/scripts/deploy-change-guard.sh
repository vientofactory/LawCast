#!/bin/bash
# Deploy change guard: compare the incoming git HEAD against the record of
# what was last successfully deployed for a service, so a push carrying no
# actual service changes exits before docker build.
#
# Usage: deploy-change-guard.sh check|record <service>
#   check  -> exit 0 when the deploy can be skipped (no actual changes),
#             exit 1 when a deploy is needed. Any state the guard cannot
#             read (missing/corrupt marker, unknown history) fails open
#             into a deploy.
#   record -> write the marker after a deploy passed its health check.
#
# The marker lives OUTSIDE the checkout (${REPO_ROOT}.deploy-state/), so the
# workflows' `git clean -fd` cannot delete it, and it is per service so the
# two deploy jobs that share the server checkout cannot contaminate each
# other (the previous LOCAL==REMOTE check in deploy-backend.yml skipped the
# second service to run regardless of its own changes).
#
# Marker format: "<root-sha> <code-submodule-sha>". Both must match (or the
# root diff must be empty for the service's paths) before a skip is allowed:
# the workflows sync submodules with `--remote`, so the deployed code can
# move through the submodule repository without the root gitlink changing.

set -euo pipefail

ACTION="${1:?usage: deploy-change-guard.sh check|record <service>}"
SERVICE="${2:?service argument required}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="${REPO_ROOT}.deploy-state"
MARKER="$STATE_DIR/$SERVICE.sha"

# Paths whose changes make a redeploy necessary for each service.
case "$SERVICE" in
  backend)
    PATHS=(backend docker-compose.yml deploy.sh .github/workflows/deploy-backend.yml)
    ;;
  semantic-search)
    PATHS=(semantic-search docker-compose.yml deploy.sh .github/workflows/deploy-semantic-search.yml)
    ;;
  *)
    echo "[guard] unknown service: $SERVICE" >&2
    exit 1
    ;;
esac

NEW_ROOT="$(git -C "$REPO_ROOT" rev-parse HEAD)"
NEW_SUB="$(git -C "$REPO_ROOT/$SERVICE" rev-parse HEAD)"

record() {
  mkdir -p "$STATE_DIR"
  echo "$NEW_ROOT $NEW_SUB" > "$MARKER"
  echo "[guard] recorded $SERVICE deploy: root=${NEW_ROOT:0:12} ${SERVICE}=${NEW_SUB:0:12}"
}

should_skip() {
  [ -f "$MARKER" ] || return 1
  local OLD_ROOT OLD_SUB
  read -r OLD_ROOT OLD_SUB < "$MARKER" || return 1
  [ -n "${OLD_SUB:-}" ] || return 1
  # The service code itself moved -> deploy, whatever the root says.
  [ "$OLD_SUB" = "$NEW_SUB" ] || return 1
  # Identical root commit -> nothing anywhere changed.
  [ "$OLD_ROOT" = "$NEW_ROOT" ] && return 0
  # Root moved: deploy only if the move touched this service's paths.
  git -C "$REPO_ROOT" cat-file -e "${OLD_ROOT}^{commit}" 2>/dev/null || return 1
  git -C "$REPO_ROOT" diff --quiet "$OLD_ROOT" "$NEW_ROOT" -- "${PATHS[@]}"
}

case "$ACTION" in
  check)
    if should_skip; then
      echo "[guard] $SERVICE: no actual changes since last deploy (marker root matches or is irrelevant); skip deploy"
      exit 0
    fi
    echo "[guard] $SERVICE: changes detected against last-deploy record; deploying"
    exit 1
    ;;
  record)
    record
    ;;
  *)
    echo "[guard] unknown action: $ACTION" >&2
    exit 1
    ;;
esac
