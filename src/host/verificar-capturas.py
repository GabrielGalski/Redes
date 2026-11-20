#!/usr/bin/env python3
"""Abre os quatro pcapng no Wireshark real, sem janela visível, e confere os quadros."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
output = []
with tempfile.TemporaryDirectory(prefix='cardeal-wireshark-') as directory:
    temporary = Path(directory)
    helper = temporary/'abrir.lua'
    shutil.copyfile(ROOT/'src/testes/abrir-captura.lua', helper)
    for name in ('dhcp','dns','http','email'):
        path = temporary/(name+'.pcapng')
        shutil.copyfile(ROOT/'wireshark'/path.name, path)
        metadata = subprocess.check_output(['capinfos', '-t', '-c', str(path)], text=True)
        frames = subprocess.check_output(['tshark','-n','-r',str(path),'-T','fields','-e','frame.number'], text=True).splitlines()
        result = subprocess.run(['wireshark','-n','-r',str(path),'-X','lua_script:'+str(helper)],
            env={**os.environ, 'QT_QPA_PLATFORM':'offscreen'}, capture_output=True, text=True, timeout=30, check=True)
        match = re.search(r'CARDEAL_WIRESHARK_GUI=true; QUADROS=(\d+)', result.stdout)
        if not match or int(match.group(1)) != len(frames) or not frames:
            raise RuntimeError('Leitura gráfica incompleta: '+name)
        output.append(f'{name}.pcapng: Wireshark GUI=true; quadros={len(frames)}; resultado=APROVADO\n'+metadata)
text = '\n'.join(output)
evidence = ROOT/'evidencias'/('v'+(ROOT/'VERSION').read_text().strip())
(evidence/'verificacao-wireshark.txt').write_text(text)
print(text)
