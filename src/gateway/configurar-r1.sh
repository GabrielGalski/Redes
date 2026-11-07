#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard gateway
LAN_MAC=08:00:27:ca:01:02
WAN_MAC=08:00:27:ca:01:01
LAN_IF=$(interface_for_mac "$LAN_MAC")
WAN_IF=$(interface_for_mac "$WAN_MAC")
install_r1_packages kea-dhcp4-server nftables wireshark-common curl ca-certificates
render networkd/wan.network.in /etc/systemd/network/10-cardeal-wan.network
configure_network gateway
networkctl reconfigure "$WAN_IF"
printf 'net.ipv4.ip_forward=1\n' > /etc/sysctl.d/99-cardeal-forward.conf
sysctl -p /etc/sysctl.d/99-cardeal-forward.conf
render gateway/nftables.conf.in /etc/nftables.conf
nft -c -f /etc/nftables.conf
systemctl enable nftables
systemctl restart nftables
render dhcp/kea-dhcp4.conf.in /etc/kea/kea-dhcp4.conf
kea-dhcp4 -t /etc/kea/kea-dhcp4.conf
systemctl enable kea-dhcp4-server
systemctl restart kea-dhcp4-server
systemctl is-active nftables kea-dhcp4-server
echo 'Gateway e DHCP configurados.'
