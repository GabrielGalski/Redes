#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard servidor
LAN_MAC=08:00:27:ca:02:01
BOOT_MAC=08:00:27:ca:02:02
LAN_IF=$(interface_for_mac "$LAN_MAC")
install_r1_packages bind9 bind9-utils bind9-dnsutils curl ca-certificates
render dns/named.conf.options.in /etc/bind/named.conf.options
render dns/named.conf.local.in /etc/bind/named.conf.local
render dns/db.cardeal.local.in /etc/bind/db.cardeal.local
render dns/db.cardeal.rev.in /etc/bind/db.cardeal.rev
named-checkconf
named-checkzone "$LAB_DOMAIN" /etc/bind/db.cardeal.local
named-checkzone "$LAB_REVERSE_ZONE" /etc/bind/db.cardeal.rev
configure_network servidor
systemctl enable named
systemctl restart named
systemctl is-active named
dig @127.0.0.1 "www.$LAB_DOMAIN" A +short
echo 'DNS interno e encaminhamento externo configurados.'
