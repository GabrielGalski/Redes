#!/usr/bin/env python3
"""Registra recursos e versões reais dos convidados e das ferramentas do hospedeiro."""
from concurrent.futures import ThreadPoolExecutor
import shlex
import shutil
import lab

packages = {
    'gateway': ['kea-dhcp4-server','nftables','wireshark-common'],
    'servidor': ['bind9','apache2','samba','samba-common-bin','nftables','postfix','dovecot-core','dovecot-imapd','openssl'],
    'cliente': ['bind9-dnsutils','curl','smbclient','wireshark-common','swaks'],
}
def collect(role):
    query = ['dpkg-query','-W','-f=${binary:Package}\t${Version}\n', *packages[role]]
    command = '\n'.join(['hostname','uname -r','ip -br address','free -m','df -h /', shlex.join(query)])
    (lab.EVIDENCE/f'recursos-{role}.txt').write_text(lab.ssh(role, command, capture=True).stdout)
    query = ['dpkg-query','-W','-f=${binary:Package}\t${Version}\t${db:Status-Abbrev}\n']
    (lab.EVIDENCE/f'pacotes-{role}.txt').write_text(lab.ssh(role,shlex.join(query),capture=True).stdout)
with ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(collect, lab.ROLES))
(lab.EVIDENCE/'vmstat-host.txt').write_text(lab.run(['vmstat','1','5'],capture=True).stdout)
host = (lab.Path('/etc/os-release')).read_text()
host += lab.run(['uname','-a'],capture=True).stdout
host += lab.run(['VBoxManage','--version'],capture=True).stdout
for command in (['tshark','--version'], ['pandoc','--version'], ['firefox','--version'], ['git','--version']):
    result = lab.run(command,capture=True,check=False)
    host += ' '.join(command)+': '+result.stdout.splitlines()[0]+'\n'
(lab.EVIDENCE/'recursos-hospedeiro.txt').write_text(host)
shutil.copyfile(lab.EVIDENCE/'reconstrucao/imagem-debian.json', lab.EVIDENCE/'imagem-debian.json')
for name in ('postfix','dovecot'):
    result = lab.ssh('servidor', f'sudo -n cat /var/log/{name}.log', capture=True)
    (lab.EVIDENCE/f'log-{name}.txt').write_text(result.stdout)
messages = lab.json.loads((lab.EVIDENCE/'mensagens-capturadas.json').read_text())
mail_log = (lab.EVIDENCE/'log-postfix.txt').read_text()
for item in messages:
    if not any(item['queue_id'] in line and 'status=sent' in line for line in mail_log.splitlines()):
        raise RuntimeError('Log local não confirmou entrega da fila '+item['queue_id'])
print('Recursos, inventário APT, versões e logs de entrega das mensagens capturadas registrados.')
