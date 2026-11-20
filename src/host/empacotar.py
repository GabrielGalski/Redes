#!/usr/bin/env python3
"""Organiza a entrega sem discos, credenciais privadas ou arquivos de planejamento local."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
version = (ROOT/'VERSION').read_text().strip()
output = ROOT/'entrega'
output.mkdir(exist_ok=True)
required = [ROOT/'logs/relatorio'/name for name in ('relatorio.md','relatorio.html','relatorio.pdf')]
required += [ROOT/'wireshark'/f'{name}.pcapng' for name in ('dhcp','dns','http','email')]
for path in required:
    if not path.is_file():
        raise SystemExit('Artefato obrigatório ausente: '+str(path.relative_to(ROOT)))
manifest = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in required}
(ROOT/'evidencias'/('v'+version)/'manifesto-entrega.json').write_text(json.dumps(manifest, indent=2)+'\n')
paths = ('README.md','VERSION','requirements.txt','lab.sh',
    'config/lab.env.example','config/debian-image.json','config/email-demo.json','config/packages',
    'src','templates','topologia','wireshark','evidencias','logs')
archive_path = output/f'cardeal-v{version}.tar.gz'
def allowed(info):
    parts = Path(info.name).parts
    if '__pycache__' in parts or info.name.endswith(('.pyc','.swp')):
        return None
    return info
with tarfile.open(archive_path, 'w:gz') as archive:
    for name in paths:
        archive.add(ROOT/name, arcname=name, filter=allowed)
manifest[str(archive_path.relative_to(ROOT))] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
(output/'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name,digest in manifest.items()))
print('Entrega:',archive_path.relative_to(ROOT))
print('Conferir a partir da raiz: sha256sum -c entrega/SHA256SUMS')
