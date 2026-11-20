#!/usr/bin/env python3
"""Aceite real SMTP/IMAP, sem bibliotecas externas ou exposição de senha nos logs."""
import email
from email import policy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

if os.geteuid() != 0 or Path('/etc/cardeal-role').read_text().strip() != 'cliente':
    raise SystemExit('Executar como root na VM cliente.')
domain = sys.argv[1]
server = 'mail.' + domain

def run(args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check, timeout=35)

def imap(user, *, request=None, uid=None):
    url = f'imap://{server}/INBOX' + (f'/;UID={uid}' if uid else '')
    args = ['curl', '--noproxy', '*', '--silent', '--show-error', '--fail', '--max-time', '20',
            '--netrc-file', f'/etc/cardeal/credentials/{user}.netrc', '--url', url]
    if request:
        args += ['--request', request]
    return run(args).stdout

results = []
for sender, recipient in [('ana', 'bruno'), ('bruno', 'ana')]:
    message_id = f'<cardeal-{sender}-{uuid.uuid4().hex}@{domain}>'
    body = f'Mensagem interna Cardeal de {sender} para {recipient}. Identificador: {message_id}'
    print(f'=== SMTP {sender}@{domain} -> {recipient}@{domain} ===', flush=True)
    sent = run(['swaks', '--server', server, '--port', '25', '--timeout', '15', '--from', f'{sender}@{domain}',
                '--to', f'{recipient}@{domain}', '--header', f'Message-Id: {message_id}',
                '--header', f'Subject: Aceite Cardeal {sender} para {recipient}', '--body', body])
    transcript = sent.stdout + sent.stderr
    print(transcript, end='', flush=True)
    queue = re.search(r'250[^\n]*queued as ([A-Z0-9]+)', transcript)
    if not queue:
        raise RuntimeError('SMTP não confirmou enfileiramento.')
    uid = None
    for _ in range(20):
        found = imap(recipient, request=f'UID SEARCH HEADER Message-ID "{message_id}"')
        match = re.search(r'\* SEARCH ([0-9]+)', found)
        if match:
            uid = match.group(1)
            break
        time.sleep(1)
    if not uid:
        raise RuntimeError('Mensagem aceita por SMTP não apareceu no IMAP.')
    received = imap(recipient, uid=uid)
    parsed = email.message_from_string(received, policy=policy.default)
    assert len(parsed.get_all('Message-ID', [])) == 1
    assert parsed['Message-ID'] == message_id
    assert parsed['From'] == f'{sender}@{domain}'
    assert parsed['To'] == f'{recipient}@{domain}'
    assert body in parsed.get_content()
    print(f'OK: {recipient} leu por IMAP UID {uid}; Message-ID e corpo coincidem.', flush=True)
    results.append({'remetente': sender+'@'+domain, 'destinatario': recipient+'@'+domain,
                    'message_id': message_id, 'queue_id': queue.group(1), 'imap_uid': uid})

print('=== Destinatário inexistente e relay externo ===', flush=True)
for recipient, code in [(f'inexistente@{domain}', '550'), ('destinatario@example.org', '554')]:
    denied = run(['swaks', '--server', server, '--port', '25', '--timeout', '15', '--from', f'ana@{domain}',
                  '--to', recipient, '--quit-after', 'RCPT'], check=False)
    transcript = denied.stdout + denied.stderr
    print(transcript, end='', flush=True)
    if denied.returncode == 0 or not re.search(r'<\*\*\s+'+code+r'\b', transcript):
        raise RuntimeError('Rejeição SMTP esperada não foi comprovada para ' + recipient)

directory = Path('/var/lib/cardeal')
directory.mkdir(mode=0o700, exist_ok=True)
(directory/'teste-email.json').write_text(json.dumps(results, indent=2)+'\n')
print('ACEITE FUNCIONAL DO E-MAIL: APROVADO', flush=True)
