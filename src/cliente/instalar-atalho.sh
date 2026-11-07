#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard cliente

CLIENT_USER=${LAB_SSH_ADMIN_USER:-cardeal}
CLIENT_HOME=$(getent passwd "$CLIENT_USER" | cut -d: -f6)
[[ -d "$CLIENT_HOME" ]] || { echo 'Diretório inicial do usuário cliente não encontrado.' >&2; exit 1; }
install -m 755 "$PROJECT_ROOT/src/cliente/lab.sh" /usr/local/bin/cardeal-lab

SHORTCUT="$CLIENT_HOME/lab.sh"
if [[ -e "$SHORTCUT" || -L "$SHORTCUT" ]] && [[ ! -L "$SHORTCUT" || $(readlink "$SHORTCUT") != /usr/local/bin/cardeal-lab ]]; then
    printf 'Já existe %s; atalho global disponível como cardeal-lab.\n' "$SHORTCUT"
else
    ln -sfn /usr/local/bin/cardeal-lab "$SHORTCUT"
    chown -h "$CLIENT_USER" "$SHORTCUT"
fi
printf 'Testes disponíveis no cliente: ~/lab.sh testar ou cardeal-lab testar.\n'
