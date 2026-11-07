#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard cliente
LAN_IF=$(interface_for_mac 08:00:27:ca:03:01)
echo '=== Identificação e endereçamento do cliente ==='
hostname
ip -br address
ip route
networkctl status "$LAN_IF" --no-pager
resolvectl status "$LAN_IF"
IP=$(ip -4 -o address show dev "$LAN_IF" scope global | awk '{print $4}')
[[ "$IP" == */24 ]] || { echo 'Máscara DHCP incorreta.'; exit 1; }
python3 - "$IP" "$LAB_DHCP_START" "$LAB_DHCP_END" <<'PY'
import ipaddress,sys
ip=ipaddress.ip_interface(sys.argv[1]).ip
assert ipaddress.ip_address(sys.argv[2]) <= ip <= ipaddress.ip_address(sys.argv[3]), 'IP fora do pool'
PY
ip route show default | grep -F "via $LAB_GATEWAY_IP dev $LAN_IF"
resolvectl dns "$LAN_IF" | grep -F "$LAB_DNS_IP"
resolvectl domain "$LAN_IF" | grep -F "$LAB_DOMAIN"
echo 'OK: DHCP, máscara, gateway, DNS e domínio de busca.'
echo '=== DNS interno UDP/TCP, MX, PTR e resolução das aplicações ==='
[[ $(dig +short "@$LAB_DNS_IP" "www.$LAB_DOMAIN" A) == "$LAB_SERVER_IP" ]]
[[ $(dig +tcp +short "@$LAB_DNS_IP" "www.$LAB_DOMAIN" A) == "$LAB_SERVER_IP" ]]
dig +short "@$LAB_DNS_IP" "$LAB_DOMAIN" MX | grep -F "10 mail.$LAB_DOMAIN."
dig +short "@$LAB_DNS_IP" -x "$LAB_SERVER_IP" | grep -F "srv.$LAB_DOMAIN."
getent ahostsv4 "www.$LAB_DOMAIN" | grep -F "$LAB_SERVER_IP"
echo 'OK: A, MX, PTR, DNS TCP e getent.'
echo '=== Resolução e acesso externo ==='
dig "@$LAB_DNS_IP" deb.debian.org A +noall +answer
curl --fail --silent --show-error --connect-timeout 15 --max-time 45 --head https://deb.debian.org/debian/ | head -n 6
echo 'OK: cliente acessa HTTPS externo pela única interface LAN.'
echo 'ACEITE FUNCIONAL DA REDE: APROVADO'
