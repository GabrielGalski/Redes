#!/usr/bin/env bash
# Biblioteca exclusiva das VMs gerenciadas pelo projeto.
set -Eeuo pipefail
PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
# shellcheck source=/dev/null
source "$PROJECT_ROOT/config/lab.env"

guest_guard() {
    local role=$1
    [[ $EUID == 0 ]] || { echo 'Executar como root dentro da VM.' >&2; exit 1; }
    # shellcheck source=/etc/os-release
    source /etc/os-release
    [[ "$ID" == debian && "$VERSION_ID" == 13 ]] || { echo 'Requer Debian 13.' >&2; exit 1; }
    systemd-detect-virt --vm --quiet || { echo 'Requer uma VM.' >&2; exit 1; }
    [[ $(cat /etc/cardeal-role 2>/dev/null) == "$role" ]] || { echo 'VM não pertence a este papel do laboratório.' >&2; exit 1; }
}

interface_for_mac() {
    local path
    for path in /sys/class/net/*; do
        if [[ $(cat "$path/address") == "${1,,}" ]]; then
            basename "$path"
            return
        fi
    done
    echo "Interface não encontrada para MAC $1" >&2
    return 1
}

render() {
    local input=$1 output=$2 text name
    text=$(< "$PROJECT_ROOT/templates/$input")
    for name in LAB_SUBNET LAB_PREFIX LAB_REVERSE_ZONE LAB_GATEWAY_PTR LAB_SERVER_PTR LAB_NETMASK LAB_GATEWAY_IP LAB_SERVER_IP LAB_DNS_IP LAB_DOMAIN LAB_DHCP_START LAB_DHCP_END LAB_DHCP_LEASE_SECONDS LAB_DNS_FORWARDER LAN_MAC WAN_MAC BOOT_MAC LAN_IF WAN_IF; do
        if [[ -v "$name" ]]; then
            text=${text//"@$name@"/"${!name}"}
        fi
    done
    [[ "$text" != *'@LAB_'* && "$text" != *'@LAN_'* && "$text" != *'@WAN_'* && "$text" != *'@BOOT_'* ]] || { echo "Variável não resolvida em $input" >&2; exit 1; }
    install -d "$(dirname "$output")"
    printf '%s\n' "$text" > "$output"
}

install_r1_packages() {
    export DEBIAN_FRONTEND=noninteractive
    if [[ ! -f /swapfile ]]; then
        fallocate -l 1G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        printf '/swapfile none swap sw 0 0\n' >> /etc/fstab
    fi
    printf 'Acquire::Languages "none";\n' > /etc/apt/apt.conf.d/90-cardeal-lab
    for source_file in /etc/apt/sources.list.d/*.sources; do
        [[ ! -f "$source_file" ]] || sed -i 's/^Types: deb deb-src$/Types: deb/' "$source_file"
    done
    apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=30 update
    printf 'wireshark-common wireshark-common/install-setuid boolean false\n' | debconf-set-selections
    apt-get --no-remove --no-install-recommends -y install "$@"
}

configure_network() {
    local kind=$1 file
    install -d /etc/systemd/network /etc/cloud/cloud.cfg.d /etc/systemd/resolved.conf.d
    printf 'network: {config: disabled}\n' > /etc/cloud/cloud.cfg.d/99-cardeal-network.cfg
    # Arquivos gerados na criação desta VM; o marcador guest_guard protege o host.
    for file in /etc/systemd/network/*cloud-init*.network /etc/network/interfaces.d/*cloud-init*; do
        [[ ! -f "$file" ]] || rm -- "$file"
    done
    if [[ -f /etc/network/interfaces ]]; then
        printf 'auto lo\niface lo inet loopback\n' > /etc/network/interfaces
    fi
    if [[ -f /etc/netplan/50-cloud-init.yaml ]]; then
        rm /etc/netplan/50-cloud-init.yaml
        netplan generate
    fi
    systemctl disable networking.service 2>/dev/null || true
    render "networkd/$kind.network.in" /etc/systemd/network/10-cardeal-lan.network
    if [[ -n ${BOOT_MAC:-} ]]; then
        render networkd/bootstrap.network.in /etc/systemd/network/20-cardeal-bootstrap.network
    fi
    printf '[Resolve]\nMulticastDNS=no\nLLMNR=no\n' > /etc/systemd/resolved.conf.d/cardeal.conf
    systemctl enable --now systemd-networkd systemd-resolved
    ln -sfn /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
    networkctl reload
    networkctl reconfigure "$LAN_IF"
    systemctl restart systemd-resolved
}
