#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard cliente
trap 'printf "%s\n" "$?" > /tmp/cardeal-falha.status' EXIT
EXTERNAL_IP=$(getent ahostsv4 deb.debian.org | awk 'NR == 1 {print $1; exit}')
[[ -n "$EXTERNAL_IP" ]]
echo 'Aguardando o desligamento do gateway virtual.'
for _ in {1..75}; do
    if ! ping -c 1 -W 1 "$LAB_GATEWAY_IP" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
if ping -c 1 -W 1 "$LAB_GATEWAY_IP" >/dev/null 2>&1; then
    echo 'Gateway não foi desligado durante a janela de teste.'
    exit 1
fi
echo 'Gateway indisponível: confirmado.'
getent ahostsv4 "www.$LAB_DOMAIN"
echo 'OK: DNS interno continua disponível na LAN sem o gateway.'
if curl --fail --silent --show-error --connect-timeout 4 --max-time 8 --resolve "deb.debian.org:443:$EXTERNAL_IP" --head https://deb.debian.org/debian/; then
    echo 'ERRO: saída externa funcionou sem o gateway.'
    exit 1
fi
echo 'OK: saída externa falha sem o gateway.'
for _ in {1..90}; do
    if ping -c 1 -W 1 "$LAB_GATEWAY_IP" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
curl --fail --silent --show-error --retry 3 --retry-delay 2 --connect-timeout 8 --max-time 30 --head https://deb.debian.org/debian/
echo 'OK: saída externa restaurada após religar o gateway.'
