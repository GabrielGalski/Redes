#!/usr/bin/env python3
"""Laboratório local: VirtualBox NAT + rede interna; nenhuma escrita na rede do host."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path
import secrets
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
VMROOT = ROOT / "vms"
RUNTIME = VMROOT / ".runtime"
KEYDIR = VMROOT / ".ssh"
EVIDENCE = ROOT / "evidencias" / "v0.1.0"
SSH_CONFIG = KEYDIR / "config"
STATE_PATH = VMROOT / "lab-state.json"
ENV = {**os.environ, "VBOX_USER_HOME": str(VMROOT / ".virtualbox")}
ROLES = ("gateway", "servidor", "cliente")
MACS = {
    "gateway": ("080027CA0101", "080027CA0102"),
    "servidor": ("080027CA0201", "080027CA0202"),
    "cliente": ("080027CA0301", "080027CA0302"),
}


def run(args, *, capture=False, check=True, **kwargs):
    kwargs.setdefault("cwd", ROOT)
    return subprocess.run([str(a) for a in args], env=ENV, check=check,
                          text=True, capture_output=capture, **kwargs)


def vbox(*args, **kwargs):
    return run(["VBoxManage", *args], **kwargs)


def config():
    values = {}
    for path in (ROOT / "config/lab.env.example", ROOT / "config/lab.env"):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            tokens = shlex.split(value, comments=True)
            if len(tokens) > 1 or not key.startswith("LAB_"):
                raise ValueError(f"Parâmetro inválido em {path.name}: {key}")
            values[key] = tokens[0] if tokens else ""
    values["LAB_SSH_ADMIN_USER"] = values.get("LAB_SSH_ADMIN_USER") or "cardeal"
    values.setdefault("LAB_DNS_FORWARDER", "10.0.2.3")
    network = ipaddress.IPv4Network(values["LAB_SUBNET"])
    if network.prefixlen != 24:
        raise ValueError("Esta rodada aceita LAN /24.")
    for key in ("LAB_GATEWAY_IP", "LAB_SERVER_IP", "LAB_DNS_IP", "LAB_DHCP_START", "LAB_DHCP_END"):
        if ipaddress.IPv4Address(values[key]) not in network:
            raise ValueError(f"{key} deve pertencer à LAN.")
    values["LAB_PREFIX"] = "24"
    values["LAB_REVERSE_ZONE"] = ".".join(reversed(str(network.network_address).split(".")[:3])) + ".in-addr.arpa"
    values["LAB_GATEWAY_PTR"] = values["LAB_GATEWAY_IP"].split(".")[-1]
    values["LAB_SERVER_PTR"] = values["LAB_SERVER_IP"].split(".")[-1]
    if not (ipaddress.ip_address(values["LAB_DHCP_START"]) <= ipaddress.ip_address(values["LAB_DHCP_END"])):
        raise ValueError("Pool DHCP invertido.")
    for key in ("LAB_GATEWAY_IP", "LAB_SERVER_IP"):
        if ipaddress.ip_address(values["LAB_DHCP_START"]) <= ipaddress.ip_address(values[key]) <= ipaddress.ip_address(values["LAB_DHCP_END"]):
            raise ValueError("Endereço estático sobrepõe o pool DHCP.")
    return values


CFG = config()


def vm_name(role):
    key = {"gateway": "GATEWAY", "servidor": "SERVER", "cliente": "CLIENT"}[role]
    return CFG[f"LAB_{key}_VM"]


def bootstrap_port(role):
    key = {"gateway": "LAB_GATEWAY_SSH_HOST_PORT", "servidor": "LAB_SERVER_BOOTSTRAP_SSH_HOST_PORT", "cliente": "LAB_CLIENT_BOOTSTRAP_SSH_HOST_PORT"}[role]
    return int(CFG[key])


def state():
    return json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {"vms": {}, "phase": "new"}


def save_state(data):
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(STATE_PATH)


def private_dirs():
    for path in (VMROOT, RUNTIME, KEYDIR, VMROOT / ".virtualbox"):
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o700)
    EVIDENCE.mkdir(parents=True, exist_ok=True)


def vm_info(role):
    result = vbox("showvminfo", vm_name(role), "--machinereadable", capture=True, check=False)
    if result.returncode:
        return {}
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def check_owned(role):
    info = vm_info(role)
    expected = state()["vms"].get(role, {}).get("uuid")
    if not info or info.get("UUID", "").strip('"') != expected:
        raise RuntimeError(f"VM {vm_name(role)} não pertence ao estado gerenciado deste projeto.")
    return info


def host_network():
    addresses = json.loads(run(["ip", "-j", "address", "show"], capture=True).stdout)
    normalized = []
    for item in addresses:
        normalized.append({"name": item["ifname"], "mac": item.get("address"),
                           "addresses": sorted([a["family"], a["local"], a["prefixlen"]]
                                               for a in item.get("addr_info", []) if not a.get("temporary"))})
    routes = json.loads(run(["ip", "-j", "route", "show"], capture=True).stdout)
    resolv = Path("/etc/resolv.conf")
    return {"interfaces": normalized, "routes": routes,
            "resolv_target": str(resolv.resolve()), "resolv_sha256": hashlib.sha256(resolv.read_bytes()).hexdigest()}


def snapshot_network(*, check_overlap=True):
    before = host_network()
    network = ipaddress.ip_network(CFG["LAB_SUBNET"])
    for route in before["routes"] if check_overlap else []:
        dst = route.get("dst", "default")
        if dst != "default" and network.overlaps(ipaddress.ip_network(dst, strict=False)):
            raise RuntimeError(f"LAN planejada conflita com rota do hospedeiro: {dst}")
    (RUNTIME / "host-network-before.json").write_text(json.dumps(before, indent=2))


def verify_host_network():
    original = json.loads((RUNTIME / "host-network-before.json").read_text())
    current = host_network()
    ok = original == current
    (EVIDENCE / "rede-hospedeiro.json").write_text(json.dumps({
        "sem_alteracoes": ok,
        "verificacao": "interfaces, endereços estáveis IPv4/IPv6, rotas IPv4 e configuração resolv.conf",
        "antes_sha256": hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest(),
        "depois_sha256": hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest(),
    }, indent=2, ensure_ascii=False) + "\n")
    if not ok:
        raise RuntimeError("A rede do hospedeiro mudou desde o início; comparar o registro local antes de aprovar.")
    print("OK: interfaces, rotas e DNS do hospedeiro preservados.", flush=True)


def download():
    private_dirs()
    image = json.loads((ROOT / "config/debian-image.json").read_text())
    directory = ROOT / "isos"
    directory.mkdir(exist_ok=True)
    archive = directory / image["filename"]
    partial = archive.with_suffix(archive.suffix + ".part")
    if not archive.exists() and partial.exists():
        with partial.open("rb") as stream:
            if hashlib.file_digest(stream, "sha512").hexdigest() == image["sha512"]:
                partial.replace(archive)
    if not archive.exists():
        print("Baixando base Debian oficial...", flush=True)
        run(["curl", "--fail", "--location", "--retry", "2", "--connect-timeout", "20", "--max-time", "1800", "--continue-at", "-", "--output", partial, image["url"]])
        partial.replace(archive)
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha512").hexdigest()
    if digest != image["sha512"]:
        raise RuntimeError("Checksum SHA-512 da imagem Debian inválido; arquivo não será utilizado.")
    print("OK: SHA-512 da imagem Debian verificado.", flush=True)
    (EVIDENCE / "imagem-debian.json").write_text(json.dumps(image, indent=2) + "\n")
    raw = directory / "disk.raw"
    base = directory / "debian-13-base.vdi"
    if not base.exists():
        if not raw.exists():
            names = run(["tar", "-tJf", archive], capture=True).stdout.splitlines()
            if names != ["disk.raw"]:
                raise RuntimeError(f"Conteúdo inesperado no arquivo Debian: {names}")
            run(["tar", "-xJf", archive, "--sparse", "-C", directory, "disk.raw"])
        vbox("convertfromraw", raw, base, "--format", "VDI")
    return base


def setup_ssh():
    key = KEYDIR / "id_ed25519"
    if not key.exists():
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "cardeal-lab-local", "-f", key])
    key.chmod(0o600)
    write_ssh_config()


def write_ssh_config():
    client_ip = state().get("client_ip", str(ipaddress.ip_network(CFG["LAB_SUBNET"]).network_address + 20))
    text = "Host cardeal-*\n  User " + CFG["LAB_SSH_ADMIN_USER"] + "\n"
    text += f'  IdentityFile "{KEYDIR / "id_ed25519"}"\n  UserKnownHostsFile "{KEYDIR / "known_hosts"}"\n'
    text += "  IdentitiesOnly yes\n  StrictHostKeyChecking accept-new\n  BatchMode yes\n  ConnectTimeout 8\n  ServerAliveInterval 15\n  ServerAliveCountMax 4\n\n"
    for role in ROLES:
        alias = {"gateway": "cardeal-gw", "servidor": "cardeal-srv", "cliente": "cardeal-cli"}[role]
        if role == "gateway":
            text += f"Host {alias}\n  HostName 127.0.0.1\n  Port {bootstrap_port(role)}\n\n"
        else:
            ip = CFG["LAB_SERVER_IP"] if role == "servidor" else client_ip
            text += f"Host {alias}\n  HostName {ip}\n  ProxyJump cardeal-gw\n\n"
            text += f"Host {alias}-bootstrap\n  HostName 127.0.0.1\n  Port {bootstrap_port(role)}\n\n"
    SSH_CONFIG.write_text(text)
    SSH_CONFIG.chmod(0o600)


def alias(role, bootstrap=False):
    base = {"gateway": "cardeal-gw", "servidor": "cardeal-srv", "cliente": "cardeal-cli"}[role]
    return base + ("-bootstrap" if bootstrap and role != "gateway" else "")


def ssh(role, command, *, bootstrap=False, **kwargs):
    # ProxyJump propaga -F sem preservar espaços em versões do OpenSSH.
    return run(["ssh", "-F", SSH_CONFIG.relative_to(ROOT), alias(role, bootstrap), command], **kwargs)


def wait_ssh(role, *, bootstrap=False, timeout=360):
    print(f"Aguardando SSH: {vm_name(role)}...", flush=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if role == "cliente" and not bootstrap:
            refresh_client_ip()
        if ssh(role, "true", bootstrap=bootstrap, capture=True, check=False).returncode == 0:
            return
        info = vm_info(role)
        if info.get("VMState") in ('"aborted"', '"poweroff"'):
            raise RuntimeError(f"{vm_name(role)} não está executando. Confira o log serial em vms/.")
        time.sleep(3)
    raise TimeoutError(f"SSH indisponível em {vm_name(role)}; consulte vms/{vm_name(role)}/serial.log")


def refresh_client_ip():
    result = ssh("gateway", "sudo -n cat /var/lib/kea/kea-leases4.csv", capture=True, check=False)
    if result.returncode:
        return
    matching = [row for row in csv.DictReader(io.StringIO(result.stdout))
                if row.get("hwaddr", "").lower() == "08:00:27:ca:03:01"
                and row.get("state") == "0" and int(row.get("valid_lifetime", "0")) > 0]
    if matching:
        lease = max(matching, key=lambda row: int(row["expire"]))
        data = state()
        data["client_ip"] = lease["address"]
        save_state(data)
        write_ssh_config()


def wait_ready():
    # SSH pode iniciar antes de named; aguardar a função, não só a máquina.
    for role in ROLES:
        wait_ssh(role)
    checks = {
        "gateway": "systemctl is-active --quiet kea-dhcp4-server && test \"$(cat /proc/sys/net/ipv4/ip_forward)\" = 1",
        "servidor": "systemctl is-active --quiet named && dig +time=1 +tries=1 +short @127.0.0.1 "
                    + shlex.quote("www." + CFG["LAB_DOMAIN"]) + " A | grep -Fx " + shlex.quote(CFG["LAB_SERVER_IP"]),
    }
    for role, command in checks.items():
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if ssh(role, command, capture=True, check=False).returncode == 0:
                break
            time.sleep(2)
        else:
            raise TimeoutError(f"Serviços de {vm_name(role)} não ficaram prontos.")


def seed(role, folder):
    public = (KEYDIR / "id_ed25519.pub").read_text().strip()
    secret_file = RUNTIME / "acesso-console.json"
    passwords = json.loads(secret_file.read_text()) if secret_file.exists() else {}
    password = passwords.setdefault(role, secrets.token_urlsafe(18))
    secret_file.write_text(json.dumps(passwords, indent=2) + "\n")
    secret_file.chmod(0o600)
    password_hash = run(["openssl", "passwd", "-6", "-stdin"], input=password + "\n", capture=True).stdout.strip()
    metadata = {"instance-id": "cardeal-r1-" + role, "local-hostname": vm_name(role)}
    user = {"hostname": vm_name(role), "manage_etc_hosts": True, "ssh_pwauth": False, "disable_root": True,
            "users": [{"name": CFG["LAB_SSH_ADMIN_USER"], "shell": "/bin/bash", "sudo": "ALL=(ALL) NOPASSWD:ALL",
                       "lock_passwd": False, "hashed_passwd": password_hash, "ssh_authorized_keys": [public]}],
            "write_files": [{"path": "/etc/cardeal-role", "permissions": "0444", "content": role + "\n"}],
            "package_update": False, "package_upgrade": False}
    physical = []
    network = ipaddress.ip_network(CFG["LAB_SUBNET"])
    for i, mac in enumerate(MACS[role]):
        mac_text = ":".join(mac[j:j+2] for j in range(0, 12, 2)).lower()
        if (role == "gateway" and i == 0) or (role != "gateway" and i == 1):
            subnets = [{"type": "dhcp4"}]
        else:
            ip = CFG["LAB_GATEWAY_IP"] if role == "gateway" else CFG["LAB_SERVER_IP"] if role == "servidor" else str(network.network_address + 20)
            subnets = [{"type": "static", "address": ip, "netmask": CFG["LAB_NETMASK"]}]
        physical.append({"type": "physical", "name": f"enp0s{3 if i == 0 else 8}", "mac_address": mac_text, "subnets": subnets})
    seed_dir = folder / "seed"
    seed_dir.mkdir(exist_ok=True)
    (seed_dir / "meta-data").write_text(json.dumps(metadata))
    (seed_dir / "user-data").write_text("#cloud-config\n" + json.dumps(user, indent=2) + "\n")
    (seed_dir / "network-config").write_text(json.dumps({"version": 1, "config": physical}, indent=2))
    iso = folder / "seed.iso"
    run(["xorriso", "-as", "mkisofs", "-quiet", "-output", iso, "-volid", "cidata", "-joliet", "-rock", seed_dir])
    iso.chmod(0o600)
    return iso


def create_vms(base):
    data = state()
    for role in ROLES:
        if vm_info(role):
            check_owned(role)
            if data["vms"][role].get("created"):
                continue
        else:
            folder = VMROOT / vm_name(role)
            if folder.exists():
                raise RuntimeError(f"Diretório pré-existente sem VM registrada: {folder}")
            vbox("createvm", "--name", vm_name(role), "--ostype", "Debian_64", "--basefolder", VMROOT, "--register")
            info = vm_info(role)
            data["vms"][role] = {"uuid": info["UUID"].strip('"'), "created": False}
            save_state(data)
        folder = VMROOT / vm_name(role)
        key = {"gateway": "GATEWAY", "servidor": "SERVER", "cliente": "CLIENT"}[role]
        disk = folder / "disk.vdi"
        if not disk.exists():
            vbox("clonemedium", "disk", base, disk, "--format", "VDI")
            vbox("modifymedium", "disk", disk, "--resize", str(int(CFG[f"LAB_{key}_DISK_GIB"]) * 1024))
        iso = seed(role, folder)
        vbox("modifyvm", vm_name(role), "--memory", CFG[f"LAB_{key}_RAM_MIB"], "--cpus", CFG[f"LAB_{key}_CPUS"],
             "--audio-enabled", "off", "--boot1", "disk", "--boot2", "none", "--boot3", "none", "--boot4", "none",
             "--uart1", "0x3F8", "4", "--uartmode1", "file", folder / "serial.log")
        vbox("storagectl", vm_name(role), "--name", "SATA", "--add", "sata", "--controller", "IntelAhci")
        vbox("storageattach", vm_name(role), "--storagectl", "SATA", "--port", "0", "--device", "0", "--type", "hdd", "--medium", disk)
        vbox("storageattach", vm_name(role), "--storagectl", "SATA", "--port", "1", "--device", "0", "--type", "dvddrive", "--medium", iso)
        for i, mac in enumerate(MACS[role], 1):
            nat = (role == "gateway" and i == 1) or (role != "gateway" and i == 2)
            args = ["modifyvm", vm_name(role), f"--nic{i}", "nat" if nat else "intnet", f"--nictype{i}", "82540EM", f"--macaddress{i}", mac, f"--cableconnected{i}", "on"]
            args += [f"--natpf{i}", f"ssh,tcp,127.0.0.1,{bootstrap_port(role)},,22"] if nat else [f"--intnet{i}", CFG["LAB_LAN_NAME"]]
            vbox(*args)
        data["vms"][role]["created"] = True
        save_state(data)


def start(role):
    info = check_owned(role)
    if info.get("VMState") != '"running"':
        vbox("startvm", vm_name(role), "--type", "headless")


def stop(role):
    info = check_owned(role)
    if info.get("VMState") == '"poweroff"':
        return
    vbox("controlvm", vm_name(role), "acpipowerbutton")
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if vm_info(role).get("VMState") == '"poweroff"':
            return
        time.sleep(2)
    raise TimeoutError(f"{vm_name(role)} não desligou por ACPI; não foi forçado desligamento.")


def payload():
    path = RUNTIME / "payload.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        for name in ("src", "templates", "config/packages", "config/lab.env.example"):
            archive.add(ROOT / name, arcname=name)
        content = "\n".join(f"{k}={shlex.quote(v)}" for k, v in CFG.items()) + "\n"
        entry = tarfile.TarInfo("config/lab.env")
        entry.size = len(content.encode())
        entry.mode = 0o600
        archive.addfile(entry, io.BytesIO(content.encode()))
    return path


def provision():
    data = state()
    is_bootstrap = data.get("phase") != "ready"
    bundle = payload()
    for role in ROLES:
        start(role)
        role_bootstrap = is_bootstrap and (role == "gateway" or vm_info(role).get("nic2") == '"nat"')
        wait_ssh(role, bootstrap=role_bootstrap)
        ssh(role, "cloud-init status --wait", bootstrap=role_bootstrap)
        run(["scp", "-F", SSH_CONFIG.relative_to(ROOT), bundle, f"{alias(role, role_bootstrap)}:/tmp/cardeal-payload.tar.gz"])
        command = "sudo -n mkdir -p /opt/cardeal && sudo -n tar -xzf /tmp/cardeal-payload.tar.gz -C /opt/cardeal && sudo -n bash /opt/cardeal/src/" + role + "/configurar-r1.sh"
        print(f"Configurando {vm_name(role)}...", flush=True)
        with (EVIDENCE / f"provisionamento-{role}.txt").open("w") as log:
            result = ssh(role, command, bootstrap=role_bootstrap, stdout=log, stderr=subprocess.STDOUT, check=False)
        if result.returncode:
            tail = (EVIDENCE / f"provisionamento-{role}.txt").read_text().splitlines()[-25:]
            raise RuntimeError("Falha no provisionamento " + role + ":\n" + "\n".join(tail))
    # O lease é obtido na VM; não se assume que o primeiro endereço será .100.
    client_bootstrap = vm_info("cliente").get("nic2") == '"nat"'
    ip_json = ssh("cliente", "ip -j -4 address show dev enp0s3", bootstrap=client_bootstrap, capture=True).stdout
    addresses = json.loads(ip_json)[0]["addr_info"]
    pool = (ipaddress.ip_address(CFG["LAB_DHCP_START"]), ipaddress.ip_address(CFG["LAB_DHCP_END"]))
    leased = [x["local"] for x in addresses if pool[0] <= ipaddress.ip_address(x["local"]) <= pool[1]]
    if not leased:
        raise RuntimeError("O cliente ainda não obteve lease na LAN.")
    data["client_ip"] = leased[0]
    save_state(data)
    write_ssh_config()
    if is_bootstrap:
        for role in ("servidor", "cliente"):
            if vm_info(role).get("nic2") == '"nat"':
                stop(role)
                vbox("modifyvm", vm_name(role), "--natpf2", "delete", "ssh", "--nic2", "none")
            start(role)
            wait_ssh(role)
    data["phase"] = "ready"
    save_state(data)
    print("Topologia final: NAT apenas no gateway; servidor e cliente somente na LAN.", flush=True)


def status():
    for role in ROLES:
        info = vm_info(role)
        print(vm_name(role), info.get("VMState", "não criada").strip('"'))
    if state().get("phase") == "ready":
        print("Cliente:", state()["client_ip"], "| acesso: ./lab.sh cliente")


def test_network():
    wait_ready()
    for role in ROLES:
        info = check_owned(role)
        (EVIDENCE / f"virtualbox-{role}.txt").write_text("\n".join(f"{k}={v}" for k, v in info.items()) + "\n")
        if role != "gateway" and (info.get("nic1") != '"intnet"' or info.get("nic2") != '"none"'):
            raise RuntimeError("Cliente/servidor com interface externa adicional.")
    with (EVIDENCE / "teste-rede.txt").open("w") as output:
        result = ssh("cliente", "sudo -n bash /opt/cardeal/src/testes/testar-rede.sh", stdout=output, stderr=subprocess.STDOUT, check=False)
    print((EVIDENCE / "teste-rede.txt").read_text(), end="")
    if result.returncode:
        raise RuntimeError("Teste funcional do cliente reprovado.")


def capture_packets():
    capture_dir = ROOT / "wireshark"
    capture_dir.mkdir(exist_ok=True)
    commands = [
        ("dhcp", "gateway", "enp0s8", "udp port 67 or udp port 68", 65),
        ("dns", "cliente", "enp0s3", "port 53", 12),
    ]
    for name, role, interface, capture_filter, duration in commands:
        path = f"/tmp/cardeal-{name}.pcapng"
        ssh(role, f"sudo -n rm -f {path}")
        command = f"sudo -n dumpcap -q -p -i {interface} -f {shlex.quote(capture_filter)} -a duration:{duration} -w {path}"
        with (EVIDENCE / f"coleta-{name}.txt").open("w") as log:
            process = subprocess.Popen(["ssh", "-F", str(SSH_CONFIG.relative_to(ROOT)), alias(role), command], env=ENV, cwd=ROOT,
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(20):
                    if ssh(role, f"sudo -n test -f {path}", check=False, capture=True).returncode == 0:
                        break
                    if process.poll() is not None:
                        raise RuntimeError(f"Coletor {name} terminou antes da captura.")
                    time.sleep(1)
                else:
                    raise RuntimeError(f"Coletor {name} não ficou pronto.")
                if name == "dhcp":
                    stop("cliente")
                    start("cliente")
                    wait_ssh("cliente")
                else:
                    ssh("cliente", f"dig @{CFG['LAB_DNS_IP']} www.{CFG['LAB_DOMAIN']} A; dig +tcp @{CFG['LAB_DNS_IP']} {CFG['LAB_DOMAIN']} MX")
                if process.wait(timeout=duration + 30) != 0:
                    raise RuntimeError(f"Falha na coleta {name}; conferir seu log.")
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
        ssh(role, f"sudo -n chmod 644 {path}")
        run(["scp", "-F", SSH_CONFIG.relative_to(ROOT), f"{alias(role)}:{path}", capture_dir / f"{name}.pcapng"])
    analyze_packets()


def analyze_packets():
    # O perfil AppArmor padrão do TShark no Ubuntu permite o diretório temporário.
    # Manter as capturas originais no projeto e não modificar o perfil do sistema.
    with tempfile.TemporaryDirectory(prefix="cardeal-capturas-") as directory:
        temporary = Path(directory)
        for name in ("dhcp", "dns"):
            shutil.copyfile(ROOT / "wireshark" / f"{name}.pcapng", temporary / f"{name}.pcapng")
        dhcp = run(["tshark", "-r", temporary / "dhcp.pcapng", "-Y", "dhcp", "-T", "fields",
                    "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst", "-e", "dhcp.option.dhcp"], capture=True).stdout
        dns = run(["tshark", "-r", temporary / "dns.pcapng", "-Y", "dns", "-T", "fields",
                   "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst", "-e", "dns.qry.name", "-e", "dns.flags.response"], capture=True).stdout
        ack = run(["tshark", "-r", temporary / "dhcp.pcapng", "-Y", "dhcp.option.dhcp == 5", "-V"], capture=True).stdout
    (EVIDENCE / "dhcp-ack.txt").write_text(ack)
    (EVIDENCE / "analise-dhcp.txt").write_text("Quadro\tOrigem\tDestino\tMensagem DHCP (1=Discover,2=Offer,3=Request,5=ACK)\n" + dhcp)
    messages = {row.split("\t")[-1] for row in dhcp.splitlines()}
    if not {"1", "2", "3", "5"} <= messages:
        raise RuntimeError("A captura DHCP não contém DORA completo.")
    (EVIDENCE / "analise-dns.txt").write_text("Quadro\tOrigem\tDestino\tNome\tResposta (False=consulta,True=resposta)\n" + dns)
    responses = [row.split("\t") for row in dns.splitlines()]
    if not any(len(row) == 5 and row[1] == CFG["LAB_SERVER_IP"] and row[-1].lower() in {"1", "true"} for row in responses):
        raise RuntimeError("A captura DNS não contém resposta do servidor interno.")
    print("OK: DHCP DORA e consulta/resposta DNS capturados e conferidos.")


def test_gateway_failure():
    ssh("cliente", "rm -f /tmp/cardeal-falha.status /tmp/cardeal-falha.txt; nohup sudo -n bash /opt/cardeal/src/testes/testar-falha-gateway.sh > /tmp/cardeal-falha.txt 2>&1 < /dev/null &")
    try:
        stop("gateway")
        # Janela para o cliente detectar a perda e registrar a falha da saída.
        time.sleep(20)
    finally:
        start("gateway")
        wait_ssh("gateway")
    for _ in range(45):
        result = ssh("cliente", "cat /tmp/cardeal-falha.status", capture=True, check=False)
        if result.returncode == 0:
            report = ssh("cliente", "cat /tmp/cardeal-falha.txt", capture=True).stdout
            (EVIDENCE / "teste-falha-gateway.txt").write_text(report)
            print(report, end="")
            if result.stdout.strip() != "0":
                raise RuntimeError("Teste de perda/retorno do gateway reprovado.")
            test_network()
            return
        time.sleep(2)
    raise TimeoutError("Cliente não concluiu o teste do gateway; o gateway foi religado.")


def prepare():
    private_dirs()
    for tool in ("VBoxManage", "ssh", "scp", "ssh-keygen", "curl", "xorriso", "openssl", "xz", "tar"):
        if not shutil.which(tool):
            raise RuntimeError(f"Dependência do hospedeiro ausente: {tool}")
    if not (RUNTIME / "host-network-before.json").exists():
        snapshot_network()
    setup_ssh()
    base = download()
    create_vms(base)
    provision()
    test_network()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preparar", "baixar", "iniciar", "parar", "status", "cliente", "testar", "reiniciar", "capturar", "analisar", "testar-falha"))
    args = parser.parse_args()
    network_operation = args.command in {"preparar", "iniciar", "parar", "testar", "reiniciar", "capturar", "testar-falha"}
    if network_operation:
        private_dirs()
        # Comparar cada operação com seu início, permitindo uso em outras redes
        # legítimas em dias posteriores sem atribuir a mudança ao laboratório.
        initial = RUNTIME / "host-network-inicial.json"
        previous = RUNTIME / "host-network-before.json"
        if previous.exists() and not initial.exists():
            shutil.copyfile(previous, initial)
        snapshot_network(check_overlap=args.command == "preparar")
    if args.command == "preparar":
        prepare()
    elif args.command == "baixar":
        download()
    elif args.command == "iniciar":
        for role in ROLES:
            start(role)
        wait_ready()
        print("Cliente pronto. No Ubuntu: ./lab.sh cliente para entrar ou ./lab.sh testar para validar.")
    elif args.command == "parar":
        for role in reversed(ROLES):
            stop(role)
    elif args.command == "reiniciar":
        for role in reversed(ROLES):
            stop(role)
        for role in ROLES:
            start(role)
        test_network()
    elif args.command == "cliente":
        if state().get("phase") != "ready":
            raise RuntimeError("Execute ./lab.sh preparar antes do acesso ao cliente.")
        os.chdir(ROOT)
        print("Entrando na VM cliente. Dentro dela: ./lab.sh testar. Para retornar ao Ubuntu: exit.", flush=True)
        tty = ["-t"] if sys.stdin.isatty() else ["-T"]
        os.execvpe("ssh", ["ssh", *tty, "-F", str(SSH_CONFIG.relative_to(ROOT)), "cardeal-cli"], ENV)
    elif args.command == "testar":
        test_network()
    elif args.command == "capturar":
        capture_packets()
    elif args.command == "analisar":
        analyze_packets()
    elif args.command == "testar-falha":
        test_gateway_failure()
    else:
        status()
    if network_operation:
        verify_host_network()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, TimeoutError, subprocess.CalledProcessError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr[-2000:], file=sys.stderr)
        sys.exit(1)
