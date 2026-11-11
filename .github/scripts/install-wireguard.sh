#!/usr/bin/env bash
set -euo pipefail

if command -v wg >/dev/null && command -v wg-quick >/dev/null; then
  wg --version
  exit 0
fi

# Isolate signed Ubuntu sources from a broken hosted-runner mirror list.
# The override is useful for fixture tests; deployment uses /etc/os-release.
source "${LAWCAST_OS_RELEASE_FILE:-/etc/os-release}"
: "${VERSION_CODENAME:?Ubuntu codename is required}"
WORK=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/lawcast-wireguard.XXXXXX")
chmod 755 "$WORK"
mkdir "$WORK/lists"
for SUITE in "$VERSION_CODENAME" "$VERSION_CODENAME-updates" "$VERSION_CODENAME-security"; do
  printf 'deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://archive.ubuntu.com/ubuntu/ %s main restricted universe multiverse\n' "$SUITE"
done > "$WORK/ubuntu.list"

APT_OPTIONS=(
  -o "Dir::Etc::sourcelist=$WORK/ubuntu.list"
  -o 'Dir::Etc::sourceparts=-'
  -o "Dir::State::lists=$WORK/lists"
  -o 'APT::Update::Error-Mode=any'
  -o 'Acquire::Retries=1'
  -o 'Acquire::http::Timeout=20'
  -o 'Acquire::https::Timeout=20'
)
sudo apt-get "${APT_OPTIONS[@]}" update -qq
sudo apt-get "${APT_OPTIONS[@]}" install -y -qq wireguard-tools
wg --version
command -v wg-quick
