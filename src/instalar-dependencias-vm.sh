#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
# shellcheck source=src/common/packages.sh
source "$PROJECT_ROOT/src/common/packages.sh"

usage() {
    printf 'Uso: bash src/instalar-dependencias-vm.sh gateway|servidor|cliente --check|--plan|--install\n'
    printf 'Executar dentro da VM Debian 13 correspondente. --install exige root.\n'
}
[[ $# -eq 2 ]] || { usage; exit 2; }
ROLE=$1
MODE=$2
case "$ROLE" in
    gateway) EXPECTED_HOSTNAME=cardeal-gw ;;
    servidor) EXPECTED_HOSTNAME=cardeal-srv ;;
    cliente) EXPECTED_HOSTNAME=cardeal-cli ;;
    *) usage; exit 2 ;;
esac
case "$MODE" in
    --check|--plan|--install) ;;
    *) usage; exit 2 ;;
esac
# shellcheck source=/etc/os-release
source /etc/os-release
[[ "$ID" == debian && "$VERSION_ID" == 13 ]] || die 'Instalação de serviços permitida somente em Debian 13, nunca no hospedeiro Ubuntu.'
[[ $(dpkg --print-architecture) == amd64 ]] || die 'Arquitetura esperada: amd64.'
systemd-detect-virt --vm --quiet || die 'Execute dentro de uma máquina virtual.'
[[ $(hostname -s) == "$EXPECTED_HOSTNAME" ]] || die "Hostname esperado para este papel: $EXPECTED_HOSTNAME"

load_packages "$PROJECT_ROOT/config/packages/base-debian.txt" "$PROJECT_ROOT/config/packages/$ROLE-debian.txt"
case "$MODE" in
    --check)
        check_packages
        ((${#MISSING_PACKAGES[@]} == 0))
        ;;
    --plan)
        check_candidates
        apt-get --simulate --no-remove install "${PACKAGES[@]}"
        ;;
    --install)
        [[ $EUID -eq 0 ]] || die 'Execute como root dentro da VM.'
        export DEBIAN_FRONTEND=noninteractive
        apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 update
        check_candidates
        # Impedir a inicialização automática dos novos serviços ainda sem configuração.
        # Preservar uma política local preexistente, caso já exista.
        POLICY_CREATED=0
        cleanup() {
            if [[ "$POLICY_CREATED" == 1 ]]; then
                rm -f -- /usr/sbin/policy-rc.d
            fi
        }
        trap cleanup EXIT
        if [[ ! -e /usr/sbin/policy-rc.d && ! -L /usr/sbin/policy-rc.d ]]; then
            POLICY_CREATED=1
            printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
            chmod 755 /usr/sbin/policy-rc.d
        fi
        if [[ "$ROLE" == servidor ]] && ! package_installed postfix; then
            printf 'postfix postfix/main_mailer_type select Local only\n' | debconf-set-selections
        fi
        printf 'wireshark-common wireshark-common/install-setuid boolean false\n' | debconf-set-selections
        apt-get --no-remove --no-install-recommends install -y "${PACKAGES[@]}"
        cleanup
        POLICY_CREATED=0
        check_packages
        printf 'Dependências instaladas. Rede e serviços ainda precisam de configuração e habilitação.\n'
        ;;
esac
