#!/usr/bin/env python3
"""Inventário sem senhas, para comparar dados/permissões após reinício/reaplicação."""
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
from email.parser import BytesParser
from email import policy

if os.geteuid() != 0 or Path('/etc/cardeal-role').read_text().strip() != 'servidor':
    raise SystemExit('Executar como root na VM servidor do laboratório.')
root = Path('/srv/samba/compartilhado')
data = {'usuarios': {}, 'grupo': {}, 'arquivos': {}, 'diretorios': {}}
for user in ('ana', 'bruno'):
    entry = pwd.getpwnam(user)
    data['usuarios'][user] = {'uid': entry.pw_uid, 'gid': entry.pw_gid, 'home': entry.pw_dir,
                             'ocorrencias': sum(row.pw_name == user for row in pwd.getpwall())}
group = grp.getgrnam('funcionarios')
data['grupo'] = {'gid': group.gr_gid, 'membros': sorted(group.gr_mem)}
for path in [root, *sorted(root.rglob('*'))]:
    info = path.stat()
    item = {'uid': info.st_uid, 'gid': info.st_gid, 'modo': oct(info.st_mode & 0o7777)}
    if path.is_file():
        item['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        item['bytes'] = info.st_size
        data['arquivos'][str(path.relative_to(root))] = item
    elif path.is_dir():
        data['diretorios'][str(path.relative_to(root))] = item
data['contas_samba'] = sorted(subprocess.check_output(['pdbedit', '-L'], text=True).splitlines())
data['email'] = {}
for user in ('ana', 'bruno'):
    messages = []
    for folder in ('cur', 'new'):
        for path in (Path(pwd.getpwnam(user).pw_dir) / 'Maildir' / folder).glob('*'):
            if not path.is_file():
                continue
            raw = path.read_bytes()
            msg = BytesParser(policy=policy.default).parsebytes(raw)
            info = path.stat()
            messages.append({'message_id': str(msg.get('Message-ID', '')), 'sha256': hashlib.sha256(raw).hexdigest(),
                             'bytes': len(raw), 'uid': info.st_uid, 'gid': info.st_gid,
                             'modo': oct(info.st_mode & 0o7777)})
    data['email'][user] = sorted(messages, key=lambda item: (item['message_id'], item['sha256']))
print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
