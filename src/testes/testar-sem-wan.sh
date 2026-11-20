#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard cliente
trap 'printf "%s\n" "$?" > /tmp/cardeal-wan.status' EXIT
EXTERNAL_IP=${1:-$(getent ahostsv4 deb.debian.org | awk 'NR==1 {print $1;exit}')}
[[ -n "$EXTERNAL_IP" ]]
sleep 4
external() {
    curl --fail --silent --show-error --connect-timeout 3 --max-time 5 \
        --resolve "deb.debian.org:443:$EXTERNAL_IP" --head https://deb.debian.org/debian/
}
if external; then echo 'WAN não foi interrompida.'; exit 1; fi
bash "$PROJECT_ROOT/src/testes/testar-rede.sh" --sem-internet
bash "$PROJECT_ROOT/src/testes/testar-intranet.sh"
bash "$PROJECT_ROOT/src/testes/testar-email.sh"
if external; then echo 'WAN retornou antes do fim dos testes.'; exit 1; fi
echo 'ACEITE DA LAN SEM WAN: APROVADO'
