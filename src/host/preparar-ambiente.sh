#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
# shellcheck source=scripts/common/packages.sh
source "$PROJECT_ROOT/scripts/common/packages.sh"

usage() {
    printf 'Uso: bash scripts/host/preparar-ambiente.sh --check|--plan|--install\n'
    printf '  --check    Verifica pacotes, ferramentas e driver, sem instalar.\n'
    printf '  --plan     Simula a instalação APT, sem alterar o sistema.\n'
    printf '  --install  Instala dependências do hospedeiro; executar como root.\n'
}

[[ $# -eq 1 ]] || { usage; exit 2; }
MODE=$1
case "$MODE" in
    --check|--plan|--install) ;;
    --help) usage; exit 0 ;;
    *) usage; exit 2 ;;
esac

# shellcheck source=/etc/os-release
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 ]] || die 'Este instalador é exclusivo do hospedeiro Ubuntu 26.04.'
[[ $(dpkg --print-architecture) == amd64 ]] || die 'Arquitetura esperada: amd64.'
load_packages "$PROJECT_ROOT/config/packages/host-ubuntu.txt"
PACKAGES+=("linux-headers-$(uname -r)")
# Firefox pode estar instalado como Snap, sem ser um pacote APT convencional.
if ! command -v firefox >/dev/null 2>&1; then
    PACKAGES+=(firefox)
fi

case "$MODE" in
    --check)
        printf 'Hospedeiro: %s; kernel %s\n' "$PRETTY_NAME" "$(uname -r)"
        check_packages
        failed=0
        ((${#MISSING_PACKAGES[@]} == 0)) || failed=1
        for tool in VBoxManage wireshark dumpcap tshark capinfos ssh scp git shellcheck dot pandoc firefox curl ip ping; do
            if command -v "$tool" >/dev/null 2>&1; then
                printf 'FERRAMENTA OK       %s\n' "$tool"
            else
                printf 'FERRAMENTA PENDENTE %s\n' "$tool"
                failed=1
            fi
        done
        if [[ -r /dev/vboxdrv && -w /dev/vboxdrv ]]; then
            printf 'DRIVER OK: /dev/vboxdrv acessível ao usuário atual.\n'
        else
            printf 'DRIVER PENDENTE: /dev/vboxdrv ausente ou sem permissão de acesso.\n'
            failed=1
        fi
        printf 'O teste de inicialização das três VMs será feito após a criação delas.\n'
        exit "$failed"
        ;;
    --plan)
        check_candidates
        apt-get --simulate --no-remove install "${PACKAGES[@]}"
        ;;
    --install)
        [[ $EUID -eq 0 ]] || die 'Execute este modo com sudo em um terminal do hospedeiro.'
        # Não substituir silenciosamente uma instalação proveniente da Oracle.
        for oracle_package in virtualbox-7.0 virtualbox-7.1 virtualbox-7.2; do
            if package_installed "$oracle_package"; then
                die "Instalação Oracle detectada ($oracle_package). Este script usa os pacotes Ubuntu."
            fi
        done
        export DEBIAN_FRONTEND=noninteractive
        apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 update
        check_candidates
        # A GUI analisará arquivos; não é necessário conceder captura no host.
        printf 'wireshark-common wireshark-common/install-setuid boolean false\n' | debconf-set-selections
        apt-get --no-remove install -y "${PACKAGES[@]}"
        if ! modprobe vboxdrv; then
            printf 'Pacotes instalados, mas o driver VirtualBox não carregou.\n' >&2
            printf 'Confira dkms status, kernel/headers e Secure Boot antes de criar as VMs.\n' >&2
            exit 1
        fi
        printf 'Dependências instaladas. Execute --check como usuário normal.\n'
        ;;
esac
