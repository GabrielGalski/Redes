#!/usr/bin/env python3
"""Gera HTML autocontido com Pandoc e PDF com Firefox em perfil temporário."""
import base64
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/'logs/relatorio'


def main():
    subprocess.run(['pandoc', REPORT/'relatorio.md', '--standalone', '--embed-resources', '--toc',
                    '--metadata', 'title=Cardeal Ltda — Relatório final v1.0.0',
                    '--css', ROOT/'templates/relatorio/estilo.css', '-o', REPORT/'relatorio.html'], cwd=REPORT, check=True)
    temporary = ROOT/'tmp'
    temporary.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='firefox-relatorio-', dir=temporary) as directory:
        profile = Path(directory)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        (profile/'user.js').write_text(f'user_pref("marionette.port", {port});\n'
            'user_pref("browser.shell.checkDefaultBrowser", false);\n'
            'user_pref("browser.aboutwelcome.enabled", false);\n')
        with (REPORT/'exportacao-firefox.log').open('w') as log:
            process = subprocess.Popen(['firefox', '--headless', '--no-remote', '--marionette', '--profile', profile],
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            connection = None
            try:
                deadline = time.monotonic()+90
                while time.monotonic()<deadline:
                    try:
                        connection = socket.create_connection(('127.0.0.1', port), timeout=2)
                        connection.settimeout(90)
                        break
                    except OSError:
                        if process.poll() is not None:
                            raise RuntimeError('Firefox não iniciou; consultar exportacao-firefox.log.')
                        time.sleep(1)
                if connection is None:
                    raise TimeoutError('Marionette não ficou disponível no perfil temporário.')
                def receive():
                    length = b''
                    while not length.endswith(b':'):
                        chunk = connection.recv(1)
                        if not chunk:
                            raise EOFError('Firefox encerrou o protocolo de impressão.')
                        length += chunk
                    pending = int(length[:-1])
                    data = b''
                    while len(data)<pending:
                        chunk = connection.recv(pending-len(data))
                        if not chunk:
                            raise EOFError('Resposta de impressão incompleta.')
                        data += chunk
                    return json.loads(data)
                receive()
                sequence = 0
                def command(name, values):
                    nonlocal sequence
                    sequence += 1
                    data = json.dumps([0, sequence, name, values]).encode()
                    connection.sendall(str(len(data)).encode()+b':'+data)
                    response = receive()
                    if response[:2] != [1, sequence]:
                        raise RuntimeError('Resposta Marionette não corresponde ao comando enviado.')
                    if response[2]:
                        raise RuntimeError(str(response[2]))
                    return response[3]
                command('WebDriver:NewSession', {'capabilities': {}})
                command('WebDriver:Navigate', {'url': (REPORT/'relatorio.html').as_uri()})
                result = command('WebDriver:Print', {'background': True, 'orientation': 'portrait',
                    'page': {'width': 21.0, 'height': 29.7}, 'margin': {'top': 1.2, 'bottom': 1.2, 'left': 1.2, 'right': 1.2},
                    'shrinkToFit': True})
                encoded = result.get('value') if isinstance(result, dict) else result
                pdf = base64.b64decode(encoded)
                if not pdf.startswith(b'%PDF-'):
                    raise RuntimeError('Firefox não retornou um PDF válido.')
                (REPORT/'relatorio.pdf').write_bytes(pdf)
                command('WebDriver:DeleteSession', {})
            finally:
                if connection:
                    connection.close()
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=15)
    print('HTML autocontido e PDF gerados em logs/relatorio/.')


if __name__ == '__main__':
    main()
