"""Aceite dos serviços, capturas e reconstrução do laboratório.

O controlador recebido em ``lab`` fornece acesso às VMs, configuração e evidências.
"""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


def validate_server(lab):
    command = ' && '.join(['sudo -n postfix check', 'sudo -n postconf -n', 'sudo -n doveconf -n',
        'sudo -n postfix status', 'sudo -n apache2ctl configtest', 'sudo -n testparm -s',
        'sudo -n nft -c -f /etc/nftables.conf', 'systemctl is-active named apache2 smbd nftables dovecot postfix',
        'systemctl is-enabled named apache2 smbd nftables dovecot postfix', 'sudo -n ss -lntup'])
    with (lab.EVIDENCE/'validadores-servidor.txt').open('w') as output:
        result = lab.ssh('servidor', command, stdout=output, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError('Validadores nativos do servidor reprovaram; consultar evidências.')


def verify(lab):
    path = lab.EVIDENCE/'teste-integrado.txt'
    with path.open('w') as output:
        result = lab.ssh('cliente', 'sudo -n bash /opt/cardeal/src/testes/verificar-laboratorio.sh',
                         stdout=output, stderr=subprocess.STDOUT, check=False)
    print(path.read_text(), end='', flush=True)
    if result.returncode:
        raise RuntimeError('Verificação integrada reprovada; consultar teste-integrado.txt.')
    validate_server(lab)
    (lab.EVIDENCE/'mensagens-email.json').write_text(lab.ssh('cliente', 'sudo -n cat /var/lib/cardeal/teste-email.json', capture=True).stdout)
    (lab.EVIDENCE/'inventario-intranet.json').write_text(json.dumps(lab.intranet_inventory(), indent=2, ensure_ascii=False)+'\n')


def test_email(lab):
    lab.wait_ready()
    path = lab.EVIDENCE/'teste-email.txt'
    with path.open('w') as output:
        result = lab.ssh('cliente', 'sudo -n bash /opt/cardeal/src/testes/testar-email.sh',
                         stdout=output, stderr=subprocess.STDOUT, check=False)
    print(path.read_text(), end='', flush=True)
    if result.returncode:
        raise RuntimeError('Envio/leitura SMTP/IMAP reprovados.')
    validate_server(lab)
    (lab.EVIDENCE/'mensagens-email.json').write_text(lab.ssh('cliente', 'sudo -n cat /var/lib/cardeal/teste-email.json', capture=True).stdout)


def capture_email(lab):
    lab.wait_ready()
    path = '/tmp/cardeal-email.pcapng'
    lab.ssh('cliente', f'sudo -n rm -f {path}')
    command = 'sudo -n dumpcap -q -p -i enp0s3 -f ' + shlex.quote('host '+lab.CFG['LAB_SERVER_IP']+' and (tcp port 25 or tcp port 143)') + f' -a duration:25 -w {path}'
    with (lab.EVIDENCE/'coleta-email.txt').open('w') as output:
        process = subprocess.Popen(['ssh', '-F', str(lab.SSH_CONFIG.relative_to(lab.ROOT)), lab.alias('cliente'), command],
            env=lab.ENV, cwd=lab.ROOT, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
        try:
            for _ in range(20):
                if lab.ssh('cliente', f'sudo -n test -f {path}', capture=True, check=False).returncode == 0:
                    break
                if process.poll() is not None:
                    raise RuntimeError('Coletor SMTP/IMAP terminou antes da comunicação.')
                time.sleep(1)
            else:
                raise TimeoutError('Coletor SMTP/IMAP não ficou pronto.')
            test_email(lab)
            if process.wait(timeout=50):
                raise RuntimeError('Coleta SMTP/IMAP reprovada.')
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    lab.ssh('cliente', f'sudo -n chmod 644 {path}')
    lab.run(['scp', '-F', lab.SSH_CONFIG.relative_to(lab.ROOT), f'{lab.alias("cliente")}:{path}', lab.ROOT/'wireshark/email.pcapng'])
    shutil.copyfile(lab.EVIDENCE/'mensagens-email.json', lab.EVIDENCE/'mensagens-capturadas.json')
    analyze_email(lab)


def analyze_email(lab):
    fields = ('frame.number', 'ip.src', 'ip.dst', 'tcp.stream', 'tcp.dstport', 'tcp.flags.syn', 'tcp.flags.ack',
              'smtp.req.command', 'smtp.response.code', 'imap.request', 'imap.response')
    with tempfile.TemporaryDirectory(prefix='cardeal-email-') as directory:
        path = Path(directory)/'email.pcapng'
        shutil.copyfile(lab.ROOT/'wireshark/email.pcapng', path)
        args = ['tshark', '-r', path, '-Y', 'tcp', '-T', 'fields']
        for field in fields:
            args.extend(['-e', field])
        text = lab.run(args, capture=True).stdout
        smtp = lab.run(['tshark', '-r', path, '-Y', 'smtp', '-T', 'fields', '-e', 'frame.number',
                        '-e', 'smtp.req.command', '-e', 'smtp.req.parameter', '-e', 'smtp.response.code'], capture=True).stdout
    rows = [dict(zip(fields, line.split('\t'))) for line in text.splitlines()]
    truth = lambda value: value.lower() in {'true', '1'}
    initial = next((r for r in rows if r['tcp.dstport']=='25' and truth(r['tcp.flags.syn']) and not truth(r['tcp.flags.ack'])), None)
    if not initial:
        raise RuntimeError('Captura sem iniciador TCP SMTP.')
    stream = [r for r in rows if r['tcp.stream']==initial['tcp.stream']]
    banner = next((r for r in stream if r['smtp.response.code']=='220' and r['ip.src']==lab.CFG['LAB_SERVER_IP']), None)
    commands = {}
    for name in ('EHLO','MAIL','RCPT','DATA'):
        row = next((r for r in stream if name in r['smtp.req.command'].split(',') and r['ip.src']==initial['ip.src']), None)
        if not row:
            raise RuntimeError('Captura sem comando SMTP '+name)
        commands[name] = row['frame.number']
    imap_requests = [r for r in rows if r['imap.request'] and r['ip.dst']==lab.CFG['LAB_SERVER_IP']]
    imap_responses = [r for r in rows if r['imap.response'] and r['ip.src']==lab.CFG['LAB_SERVER_IP']]
    fetch = next((r for r in imap_requests if 'FETCH' in r['imap.request'].upper()), None)
    if not banner or not imap_requests or not imap_responses or not fetch:
        raise RuntimeError('Captura sem banner SMTP ou comunicação IMAP.')
    summary = {'cliente_iniciador_tcp': initial['ip.src'], 'servidor': lab.CFG['LAB_SERVER_IP'],
        'smtp_stream': initial['tcp.stream'], 'quadros': {'SYN_SMTP': initial['frame.number'],
        'banner_220': banner['frame.number'], **commands, 'primeiro_IMAP_cliente': imap_requests[0]['frame.number'],
        'primeiro_IMAP_servidor': imap_responses[0]['frame.number'], 'FETCH_IMAP': fetch['frame.number']},
        'nota': 'Captura didática contém autenticação IMAP fictícia pública; não contém credenciais SMB.'}
    (lab.EVIDENCE/'email.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False)+'\n')
    (lab.EVIDENCE/'analise-email.txt').write_text('\t'.join(fields)+'\n'+text+'\nComandos e respostas SMTP:\n'+smtp)
    print('OK: iniciador TCP, banner SMTP, EHLO/MAIL/RCPT/DATA e comunicação IMAP identificados.', flush=True)


def test_wan(lab):
    lab.wait_ready()
    external_ip = lab.ssh('cliente', 'getent ahostsv4 deb.debian.org', capture=True).stdout.split()[0]
    lab.ssh('cliente', 'rm -f /tmp/cardeal-wan.status /tmp/cardeal-wan.txt; nohup sudo -n bash /opt/cardeal/src/testes/testar-sem-wan.sh '
            + shlex.quote(external_ip) + ' > /tmp/cardeal-wan.txt 2>&1 < /dev/null &')
    try:
        lab.vbox('controlvm', lab.vm_name('gateway'), 'setlinkstate1', 'off')
        time.sleep(30)
    finally:
        lab.vbox('controlvm', lab.vm_name('gateway'), 'setlinkstate1', 'on')
    lab.wait_ready()
    status = lab.ssh('cliente', 'cat /tmp/cardeal-wan.status', capture=True).stdout.strip()
    report = lab.ssh('cliente', 'cat /tmp/cardeal-wan.txt', capture=True).stdout
    (lab.EVIDENCE/'teste-sem-wan.txt').write_text(report)
    print(report, end='', flush=True)
    if status != '0':
        raise RuntimeError('Serviços internos sem WAN reprovaram; WAN restaurada.')
    lab.test_lab()


def test_detector(lab):
    lab.wait_ready()
    try:
        lab.ssh('servidor', 'sudo -n systemctl stop apache2')
        result = lab.ssh('cliente', 'sudo -n bash /opt/cardeal/src/testes/verificar-laboratorio.sh', capture=True, check=False)
        (lab.EVIDENCE/'detector-servico-parado.txt').write_text(result.stdout+result.stderr)
        if result.returncode == 0 or 'RESULTADO INTRANET: REPROVADO' not in result.stdout:
            raise RuntimeError('Verificador não identificou a parada do Apache.')
    finally:
        lab.ssh('servidor', 'sudo -n systemctl start apache2')
    lab.test_lab()
    (lab.EVIDENCE/'detector.json').write_text(json.dumps({'apache_parado': 'REPROVADO, como esperado',
        'codigo_de_saida': result.returncode, 'apache_restaurado': 'APROVADO'}, indent=2)+'\n')
    print('OK: verificador detectou o serviço indisponível e aprovou após recuperação.', flush=True)


def reconstruct(lab):
    validation = lab.ROOT/'vms/validacao'
    if (validation/'lab-state.json').exists():
        raise RuntimeError('Validação já existe; preservar seu registro e usar os resultados existentes.')
    lab.private_dirs()
    config = lab.RUNTIME/'reconstrucao.env'
    config.write_text('LAB_GATEWAY_VM=cardeal-validacao-gw\nLAB_SERVER_VM=cardeal-validacao-srv\nLAB_CLIENT_VM=cardeal-validacao-cli\n'
        'LAB_LAN_NAME=cardeal-validacao\nLAB_GATEWAY_SSH_HOST_PORT=2232\n'
        'LAB_SERVER_BOOTSTRAP_SSH_HOST_PORT=2233\nLAB_CLIENT_BOOTSTRAP_SSH_HOST_PORT=2234\n')
    evidence = lab.EVIDENCE/'reconstrucao'
    evidence.mkdir(parents=True, exist_ok=True)
    env = {**lab.ENV, 'CARDEAL_VM_ROOT': str(validation), 'CARDEAL_CONFIG': str(config), 'CARDEAL_EVIDENCE': str(evidence)}
    executable = [sys.executable, str(lab.ROOT/'src/host/lab.py')]
    try:
        for role in reversed(lab.ROLES):
            lab.stop(role)
        print('Reconstruindo três VMs novas da imagem Debian verificada; VMs originais desligadas para limitar RAM.', flush=True)
        with (evidence/'preparacao.log').open('w') as output:
            subprocess.run([*executable, 'preparar'], cwd=lab.ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, check=True)
        with (evidence/'reinicio.log').open('w') as output:
            subprocess.run([*executable, 'reiniciar'], cwd=lab.ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, check=True)
        (lab.EVIDENCE/'reconstrucao.json').write_text(json.dumps({'resultado': 'APROVADO',
            'base': 'imagem Debian oficial, sem reutilizar discos configurados',
            'vms': ['cardeal-validacao-gw','cardeal-validacao-srv','cardeal-validacao-cli'], 'lan': 'cardeal-validacao',
            'passos_manuais_so': 'nenhum; NoCloud e scripts versionados', 'originais_preservadas': True}, indent=2)+'\n')
    finally:
        if (validation/'lab-state.json').exists():
            with (evidence/'parada.log').open('w') as output:
                subprocess.run([*executable, 'parar'], cwd=lab.ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, check=False)
        for role in lab.ROLES:
            lab.start(role)
        lab.wait_ready()
    lab.test_lab()
    print('ACEITE DE RECONSTRUÇÃO EM VMs NOVAS: APROVADO; originais novamente disponíveis.', flush=True)
