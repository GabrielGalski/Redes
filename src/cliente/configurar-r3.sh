#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard cliente
install_r1_packages swaks
install -d -m 700 /etc/cardeal/credentials
python3 - "$PROJECT_ROOT/config/email-demo.json" "$LAB_DOMAIN" <<'PY'
import json, os, sys
from pathlib import Path
demo = json.loads(Path(sys.argv[1]).read_text())
for user in ('ana', 'bruno'):
    path = Path('/etc/cardeal/credentials') / f'{user}.netrc'
    with open(path, 'w', opener=lambda name, flags: os.open(name, flags, 0o600)) as stream:
        stream.write(f'machine mail.{sys.argv[2]}\nlogin {user}\npassword {demo[user]}\n')
    path.chmod(0o600)
PY
bash "$PROJECT_ROOT/src/cliente/instalar-atalho.sh"
printf '1.0.0\n' > /etc/cardeal/version
echo 'Cliente pronto para SMTP e leitura IMAP; login local ana ou bruno.'
