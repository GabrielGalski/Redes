#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard servidor
LAN_IF=$(interface_for_mac 08:00:27:ca:02:01)
printf 'postfix postfix/main_mailer_type select Local only\npostfix postfix/mailname string %s\n' "$LAB_DOMAIN" | debconf-set-selections
install_packages postfix dovecot-core dovecot-imapd openssl
python3 - "$PROJECT_ROOT/config/email-demo.json" <<'PY'
import grp, json, os, pwd, subprocess, sys
from pathlib import Path
demo = json.loads(Path(sys.argv[1]).read_text())
lines = []
for user in ('ana', 'bruno'):
    entry = pwd.getpwnam(user)
    password_hash = subprocess.check_output(['openssl', 'passwd', '-6', '-stdin'],
        input=demo[user] + '\n', text=True).strip()
    lines.append(f'{user}:{{SHA512-CRYPT}}{password_hash}:{entry.pw_uid}:{entry.pw_gid}::{entry.pw_dir}::')
    for part in ('', 'cur', 'new', 'tmp'):
        path = Path(entry.pw_dir) / 'Maildir' / part
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chown(path, entry.pw_uid, entry.pw_gid)
        path.chmod(0o700)
path = Path('/etc/dovecot/cardeal-users')
with open(path, 'w', opener=lambda name, flags: os.open(name, flags, 0o600)) as stream:
    stream.write('\n'.join(lines) + '\n')
os.chown(path, 0, grp.getgrnam('dovecot').gr_gid)
path.chmod(0o640)
PY
render email/main.cf.in /etc/postfix/main.cf
render email/recipients.in /etc/postfix/cardeal-recipients
printf '%s\n' "$LAB_DOMAIN" > /etc/mailname
postmap /etc/postfix/cardeal-recipients
newaliases
render email/dovecot.conf.in /etc/dovecot/dovecot.conf
postfix check
doveconf -n
render email/nftables-servidor.conf.in /etc/nftables.conf
nft -c -f /etc/nftables.conf
systemctl restart nftables
systemctl enable postfix dovecot
systemctl restart postfix dovecot
postfix status
systemctl is-active dovecot
install -m 600 "$PROJECT_ROOT/VERSION" /etc/cardeal/version
echo 'SMTP interno e IMAP configurados; Maildir existente preservado.'
