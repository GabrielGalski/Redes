#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard cliente
LAN_MAC=08:00:27:ca:03:01
BOOT_MAC=08:00:27:ca:03:02
LAN_IF=$(interface_for_mac "$LAN_MAC")
install_r1_packages bind9-dnsutils curl ca-certificates wireshark-common
configure_network cliente
bash "$PROJECT_ROOT/src/cliente/instalar-atalho.sh"
echo 'Cliente configurado para receber DHCP, DNS e rota pela LAN.'
