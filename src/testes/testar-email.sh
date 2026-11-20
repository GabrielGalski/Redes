#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard cliente
exec python3 "$PROJECT_ROOT/src/testes/testar-email.py" "$LAB_DOMAIN"
