#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard servidor
LAN_IF=$(interface_for_mac 08:00:27:ca:02:01)
[[ -s /etc/cardeal/intranet.json ]] || { echo 'Credenciais locais da intranet ausentes.' >&2; exit 1; }
install_r1_packages apache2 samba samba-common-bin nftables

getent group funcionarios >/dev/null || groupadd funcionarios
for user in ana bruno; do
    id "$user" >/dev/null 2>&1 || useradd --create-home --gid funcionarios --shell /usr/sbin/nologin "$user"
    usermod --append --groups funcionarios "$user"
done
# Senhas chegam pelo stdin, sem argumentos de processo ou logs.
python3 - <<'PY'
import json, subprocess
from pathlib import Path
credentials = json.loads(Path('/etc/cardeal/intranet.json').read_text())
for user in ('ana', 'bruno'):
    password = credentials[user]
    subprocess.run(['smbpasswd', '-s', '-a', user], input=f'{password}\n{password}\n',
                   text=True, stdout=subprocess.DEVNULL, check=True)
    subprocess.run(['smbpasswd', '-e', user], stdout=subprocess.DEVNULL, check=True)
PY
install -d -o root -g funcionarios -m 2770 /srv/samba/compartilhado
install -d -o root -g funcionarios -m 2770 /srv/samba/compartilhado/aceite-cardeal
render smb/smb.conf.in /etc/samba/smb.conf
testparm -s /etc/samba/smb.conf
# SMB direto por DNS/TCP 445; sem descoberta NetBIOS ou domínio AD.
systemctl disable --now nmbd.service samba-ad-dc.service 2>/dev/null || true
systemctl enable smbd
systemctl restart smbd

install -d -m 755 /var/www/cardeal
render web/index.html.in /var/www/cardeal/index.html
install -m 644 "$PROJECT_ROOT/templates/web/estilo.css" /var/www/cardeal/estilo.css
chmod 644 /var/www/cardeal/index.html
render web/ports.conf.in /etc/apache2/ports.conf
render web/cardeal.conf.in /etc/apache2/sites-available/cardeal.conf
printf 'ServerName www.%s\nServerTokens Prod\nServerSignature Off\n' "$LAB_DOMAIN" > /etc/apache2/conf-available/cardeal.conf
a2disconf other-vhosts-access-log
a2dissite 000-default
a2enconf cardeal
a2ensite cardeal
apache2ctl configtest
systemctl enable apache2
systemctl restart apache2

render smb/nftables-servidor.conf.in /etc/nftables.conf
nft -c -f /etc/nftables.conf
systemctl enable nftables
systemctl restart nftables
systemctl is-active named apache2 smbd nftables
printf '0.2.0\n' > /etc/cardeal/version
echo 'Web, SMB autenticado e firewall LAN configurados; dados existentes preservados.'
