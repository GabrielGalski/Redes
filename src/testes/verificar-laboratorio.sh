#!/usr/bin/env bash
# Mostra o resultado de cada função e retorna erro se qualquer etapa falhar.
set -Euo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard cliente
set +e
RESULT=0
run_check() {
    local name=$1 script=$2
    if bash "$PROJECT_ROOT/src/testes/$script"; then
        printf 'RESULTADO %s: APROVADO\n' "$name"
    else
        printf 'RESULTADO %s: REPROVADO\n' "$name"
        RESULT=1
    fi
}
run_check REDE testar-rede.sh
run_check INTRANET testar-intranet.sh
run_check EMAIL testar-email.sh
if [[ $RESULT == 0 ]]; then
    echo 'ACEITE INTEGRADO DO LABORATÓRIO: APROVADO'
else
    echo 'ACEITE INTEGRADO DO LABORATÓRIO: REPROVADO'
fi
exit "$RESULT"
