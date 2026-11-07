#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard cliente
install_r1_packages smbclient
install -d -m 700 /etc/cardeal/credentials
python3 - <<'PY'
import json, os
from pathlib import Path
credentials = json.loads(Path('/etc/cardeal/intranet.json').read_text())
for user in ('ana', 'bruno'):
    path = Path('/etc/cardeal/credentials') / f'{user}.auth'
    with open(path, 'w', opener=lambda name, flags: os.open(name, flags, 0o600)) as stream:
        stream.write(f'username = {user}\npassword = {credentials[user]}\ndomain = CARDEAL\n')
    path.chmod(0o600)
PY
bash "$PROJECT_ROOT/src/cliente/instalar-atalho.sh"
printf '0.2.0\n' > /etc/cardeal/version
echo 'Cliente pronto para acessar Web e compartilhar arquivos como Ana e Bruno.'
