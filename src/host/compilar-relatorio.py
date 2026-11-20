#!/usr/bin/env python3
"""Compila o relatório final a partir das evidências reais da versão entregue."""
from datetime import datetime
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab

E = lab.EVIDENCE
R = lab.ROOT/'logs/relatorio'
def data(name):
    return json.loads((E/name).read_text())
def rows(name):
    return [line.split('\t') for line in (E/name).read_text().splitlines()[1:] if line]

assert data('persistencia.json')['reinicio']=='APROVADO'
assert data('persistencia.json')['reaplicacao']=='APROVADO'
assert data('reconstrucao.json')['resultado']=='APROVADO'
assert data('detector.json')['apache_restaurado']=='APROVADO'
assert data('rede-hospedeiro.json')['sem_alteracoes'] is True
assert 'ACEITE INTEGRADO DO LABORATÓRIO: APROVADO' in (E/'teste-integrado.txt').read_text()
assert 'ACEITE DA LAN SEM WAN: APROVADO' in (E/'teste-sem-wan.txt').read_text()
assert 'serviços LAN aprovados com gateway ainda desligado' in (E/'teste-falha-gateway.txt').read_text()
assert (E/'verificacao-wireshark.txt').read_text().count('resultado=APROVADO')==4
http = data('http.json')
mail = data('email.json')
dhcp = rows('analise-dhcp.txt')
dns = rows('analise-dns.txt')
dns_query = next(row for row in dns if row[3]=='www.'+lab.CFG['LAB_DOMAIN'] and row[4].lower() in ('false','0'))
dns_reply = next(row for row in dns if row[3]=='www.'+lab.CFG['LAB_DOMAIN'] and row[4].lower() in ('true','1'))
messages = data('mensagens-capturadas.json')
now = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M (%Z)')
dhcp_table = '\n'.join(f'| {row[0]} | `{row[1]}` | `{row[2]}` | {dict(zip(("1","2","3","5"),("Discover","Offer","Request","ACK")))[row[3]]} |'
    for row in dhcp if len(row)==4 and row[3] in ('1','2','3','5'))
message_table = '\n'.join(f'| `{row["remetente"]}` | `{row["destinatario"]}` | `{row["queue_id"]}` | {row["imap_uid"]} |'
    for row in messages)
package_rows = []
for role in lab.ROLES:
    for line in (E/f'recursos-{role}.txt').read_text().splitlines():
        if '\t' in line:
            package, version = line.split('\t',1)
            package_rows.append(f'| {role} | `{package}` | `{version}` |')
packages = '\n'.join(package_rows)
report = f'''# Projeto de infraestrutura da Cardeal Ltda

**Relatório final — v1.0.0**

Compilado em {now}. Trabalho de Redes de Computadores, UFPel, conforme o enunciado **Trabalho Infraestrutura.pdf**. As tabelas de quadros e os resultados abaixo foram obtidos nas VMs reais; o laboratório usa dados fictícios da empresa hipotética do enunciado.

## 1. Objetivo e requisitos entregues

Foi implementada uma LAN com endereçamento automático, resolução de nomes, página Web, compartilhamento de arquivos, correio interno e acesso à internet pelo gateway. A solução atende aos serviços e às quatro capturas solicitados no documento. Todos os scripts de criação, configuração, teste e geração desta entrega acompanham o projeto.

| Pedido do enunciado | Implementação e comprovação |
| --- | --- |
| DNS `cardeal.local`, incluindo `www` e `mail` | BIND, zonas direta/reversa, A/MX/PTR e consultas UDP/TCP; nomes usados pelas aplicações. |
| Página Web em servidor estático | Apache em `192.168.50.10`, HTTP 200 de `http://www.cardeal.local/`. |
| Arquivos pelo protocolo SMB | Samba autenticado, Ana e Bruno, upload/download e SHA-256 coincidente. |
| E-mail interno `usuario@cardeal.local` | Postfix SMTP e Dovecot IMAP, Ana → Bruno e Bruno → Ana com leitura efetiva. |
| DHCP, pool, máscara, gateway e DNS | Kea, `.100–.200`, `/24`, gateway `.1`, DNS `.10`; endereços estáticos fora do pool. |
| Gateway WAN/LAN e saída externa | Debian com duas NICs, encaminhamento IPv4 e NAT; cliente sem NIC NAT própria. |
| Demonstrar protocolos e rede funcionando | Verificador integrado, logs por função, falhas controladas e recuperação. |
| Capturas DHCP/DNS/HTTP/e-mail | Quatro arquivos pcapng analisados por TShark/Wireshark, com quadros indicados neste relatório. |
| Relatório, decisões, dificuldades e scripts | Este documento, README, código, templates, inventários e evidências por versão. |
| Dicas: VirtualBox, três VMs, Linux e Git | Três convidados Debian 13 em VirtualBox, sobre Ubuntu 26.04; histórico das etapas anteriores em Git. |

## 2. Infraestrutura, topologia e máquinas virtuais

![Topologia da infraestrutura implementada](../../topologia/topologia.png)

| VM | Recursos configurados | Interfaces e endereços | Funções |
| --- | --- | --- | --- |
| `cardeal-gw` | 1 vCPU, 512 MiB RAM, disco 8 GiB, swap 1 GiB | `enp0s3`: NAT/WAN por DHCP, observado `10.0.2.15/24`; `enp0s8`: LAN `192.168.50.1/24` | Kea DHCP, nftables/NAT, roteamento e salto SSH. |
| `cardeal-srv` | 2 vCPU, 1.024 MiB RAM, disco 16 GiB, swap 1 GiB | Somente `enp0s3`, LAN estática `192.168.50.10/24` | BIND, Apache, Samba, Postfix e Dovecot. |
| `cardeal-cli` | 1 vCPU, 512 MiB RAM, disco 8 GiB, swap 1 GiB | Somente `enp0s3`, DHCP observado `{lab.state()['client_ip']}/24` | Cliente dos serviços, testes e captura. |

Separar gateway, serviços e cliente permite comprovar DHCP, roteamento e acesso às aplicações a partir de outra máquina. Reunir as aplicações em um servidor mantém três convidados dentro da memória disponível do hospedeiro. A memória foi medida com todos os serviços ativos; os valores e versões estão em `evidencias/v1.0.0/recursos-*.txt`.

Os arquivos de cada VM ficam em `vms/<nome>/`: `.vbox` descreve o hardware e `disk.vdi` armazena o Debian e seus dados. O catálogo é `vms/.virtualbox/`. Discos, seeds e credenciais privadas são locais e ignorados pelo Git. A imagem oficial Debian 13, build `20261103-2651`, tem URL e SHA-512 fixados em `config/debian-image.json`; o download foi verificado antes de gerar os discos. NoCloud configura os convidados automaticamente.

## 3. Endereçamento e caminho das conexões

| Item | Configuração |
| --- | --- |
| Rede interna VirtualBox | `cardeal-lan` |
| Sub-rede / máscara | `192.168.50.0/24` / `255.255.255.0` |
| Pool DHCP inclusivo | `192.168.50.100` a `192.168.50.200` (101 endereços configurados) |
| Gateway / servidor DNS | `192.168.50.1` / `192.168.50.10` |
| IPs estáticos fora do pool | Gateway `.1` e servidor `.10` |
| Domínio e lease | `cardeal.local`, 3.600 segundos |
| Nomes apontando para `.10` | `ns`, `srv`, `www`, `files` e `mail` |
| MX | Prioridade 10, `mail.cardeal.local.` |

O cliente recebe IP, máscara, gateway, DNS e domínio por DHCP. A LAN interna faz a comunicação Ethernet entre as VMs. HTTP, SMB e correio entre cliente e servidor permanecem na mesma sub-rede, sem atravessar o gateway. A saída externa percorre cliente → gateway Debian → NAT VirtualBox → conexão existente do Ubuntu → internet.

Somente o gateway mantém NIC NAT. O NAT temporário de servidor/cliente é removido após o bootstrap. SSH do hospedeiro usa `127.0.0.1:2222` para o gateway, seguido de `ProxyJump` para os convidados da LAN. A rede virtual não é conectada por bridge à rede física e o Ubuntu não recebe uma interface host-only. A automação comparou interfaces, endereços estáveis IPv4/IPv6, rotas IPv4 e link/conteúdo de `resolv.conf`; os hashes antes/depois são iguais em `evidencias/v1.0.0/rede-hospedeiro.json`.

## 4. Configuração dos serviços

### 4.1 DNS, DHCP e gateway

BIND mantém registros internos estáticos e encaminha consultas externas ao DNS do NAT VirtualBox (`10.0.2.3`). As zonas direta e reversa foram validadas com `named-checkconf` e `named-checkzone` na configuração da base. A resolução unicast de `.local` funciona nas aplicações: networkd/resolved dos convidados desativam mDNS/LLMNR e usam o domínio configurado.

Kea atende a interface LAN do gateway e distribui as opções verificadas no ACK DHCP. O gateway habilita encaminhamento IPv4 e usa nftables para permitir LAN → WAN, retorno de conexões e masquerade da sub-rede. Conexões novas WAN → LAN permanecem bloqueadas. Os templates ficam em `templates/networkd/`, `templates/dns/`, `templates/dhcp/` e `templates/gateway/`.

### 4.2 Página Web

Apache possui VirtualHost e ServerName explícitos para `www.cardeal.local`, com conteúdo HTML/CSS estático em `/var/www/cardeal`. Escuta no IP LAN, porta 80. O teste faz GET por nome, exige código 200, confere conteúdo Cardeal e baixa o CSS. O HTTP permite observar GET/Host na captura didática. A seleção por nome segue a [documentação de VirtualHosts do Apache](https://httpd.apache.org/docs/2.4/vhosts/name-based.html).

### 4.3 Arquivos compartilhados

Samba standalone publica `//files.cardeal.local/compartilhado`, caminho `/srv/samba/compartilhado`, com grupo `funcionarios` e autenticação de `ana` e `bruno`. As contas estão separadas da administração. O diretório usa modo `2770`; arquivos usam `0660`, com leitura/escrita do grupo. SMB2/SMB3 e assinatura são exigidos pela configuração, na porta TCP 445, sem NetBIOS. As máscaras e o controle de acesso seguem o [manual smb.conf](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html).

Ana envia um arquivo e Bruno baixa os mesmos bytes. O SHA-256 verificado é `69587c5d7772a6fdaf9c4bed465f3c18785e4e476c178c29764894df6241bb37`. Bruno também consegue gravar no arquivo criado por Ana. Senha incorreta retorna `NT_STATUS_LOGON_FAILURE`; acesso anônimo ao compartilhamento retorna `NT_STATUS_ACCESS_DENIED`.

### 4.4 Correio interno SMTP e IMAP

Postfix recebe SMTP em `mail.cardeal.local:25`, com entrega local em `/home/ana/Maildir/` e `/home/bruno/Maildir/`. Dovecot lê as mesmas caixas em IMAP, porta 143. Os endereços são `ana@cardeal.local` e `bruno@cardeal.local`; o login IMAP usa apenas `ana` ou `bruno`.

Postfix restringe os destinatários a essas duas contas e usa `reject_unauth_destination`, sem liberação prévia de relay por redes confiáveis. O teste originado no cliente LAN recebe `550 5.1.1` para destinatário inexistente e `554 5.7.1` para destinatário externo. Os parâmetros nativos estão descritos no [manual Postfix](https://github.com/vdukhovni/postfix/blob/master/postfix/man/man5/postconf.5).

Dovecot 2.4 usa `dovecot_config_version`, `dovecot_storage_version`, `mail_driver`, `mail_path` e seções nomeadas de passdb/userdb. O passwd-file associa autenticação de demonstração aos UID/GID e home das contas existentes, sem alterar suas senhas SMB ou liberar shell. A sintaxe foi revisada conforme a [migração oficial para 2.4](https://doc.dovecot.org/2.4.1/installation/upgrade/2.3-to-2.4.html) e validada com `doveconf -n`.

SMTP/IMAP sem TLS são usados nesta LAN isolada para a captura didática. As credenciais de e-mail são fictícias e públicas em `config/email-demo.json`; a autenticação aparece na captura. As senhas SMB permanecem distintas, aleatórias e privadas, fora da entrega. Não há envio para a internet nem dependência de domínio público, provedor de correio, banco SQL ou serviços pagos.

## 5. Testes realizados e resultados

O comando `./lab.sh testar` executa o verificador do cliente e retorna erro se qualquer função reprovar. O resumo por função apresenta REDE, INTRANET e EMAIL, seguido do aceite integrado. `postfix check`, `postconf -n`, `doveconf -n`, `apache2ctl configtest`, `testparm` e nftables foram validados no servidor.

| Verificação | Resultado obtido |
| --- | --- |
| DHCP, máscara, rota, DNS/domínio | Aprovado; cliente recebeu os parâmetros previstos. |
| DNS A/MX/PTR, UDP/TCP e getent | Aprovado; nomes resolvidos pelo cliente. |
| HTTPS externo somente pelo gateway | Aprovado. |
| HTTP 200 e página/CSS Cardeal | Aprovado. |
| SMB Ana → Bruno, integridade e escrita do grupo | Aprovado; SHA-256 idêntico. |
| Credencial SMB incorreta e acesso anônimo | Recusados, como esperado. |
| SMTP Ana → Bruno e Bruno → Ana | Aceitos e entregues nas caixas corretas. |
| Leitura IMAP nos dois sentidos | UID, Message-ID, remetente, destinatário e corpo conferidos. |
| Destinatário inexistente / relay externo | SMTP 550 / 554, como esperado. |
| Reinício e reaplicação | Dados SMB, mensagens Maildir, contas, UID/GID e modos preservados. |
| LAN com WAN desconectada | DNS, Web, SMB e correio aprovados; saída externa indisponível. |
| Gateway desligado e religado | LAN continuou funcional; internet falhou e depois retornou. |
| Apache parado intencionalmente | Verificador retornou erro e INTRANET REPROVADO; após recuperação, aprovado. |
| Reconstrução em três VMs novas | Todos os serviços e o reinício aprovados a partir da imagem base Debian. |
| Rede do Ubuntu | Configuração preservada nas comparações. |

Os seguintes envios ocorreram durante a captura de e-mail, com IDs de fila confirmados pelo Postfix e UIDs lidos por IMAP:

| Remetente | Destinatário | ID da fila SMTP | UID IMAP |
| --- | --- | --- | --- |
{message_table}

As evidências ficam em `evidencias/v1.0.0/`: `teste-integrado.txt`, `teste-email.txt`, `mensagens-capturadas.json`, `validadores-servidor.txt`, `persistencia.json`, inventários, `teste-sem-wan.txt`, `teste-falha-gateway.txt`, `detector.json` e `reconstrucao.json`. Os logs completos estão em `logs/rodada-3/`.

## 6. Protocolos por camada

| Serviço | Aplicação | Transporte | Rede | Enlace |
| --- | --- | --- | --- | --- |
| Endereçamento | DHCP | UDP servidor 67 / cliente 68 | IPv4 | Ethernet |
| Nomes | DNS | UDP e TCP 53 | IPv4 | Ethernet |
| Página interna | HTTP/1.1 | TCP 80 | IPv4 | Ethernet |
| Arquivos | SMB2/SMB3 | TCP 445 | IPv4 | Ethernet |
| Envio de correio | SMTP | TCP 25 | IPv4 | Ethernet |
| Leitura de correio | IMAP | TCP 143 | IPv4 | Ethernet |
| Destino externo | HTTPS | TCP 443 | IPv4 | Ethernet virtual / conexão do hospedeiro |
| Administração | SSH/SCP | TCP 22, redirecionamento local 2222 | IPv4 | Ethernet virtual |
| Diagnóstico | ping (ferramenta) | — | IPv4 / ICMP | Ethernet |

ARP resolve endereços de enlace na LAN; ICMP atua na camada de rede e não utiliza portas TCP/UDP. NAT traduz endereços no gateway e no VirtualBox; não é um protocolo de aplicação. Para receber uma configuração IP, por exemplo, o cliente usa DHCP sobre UDP e IPv4, conforme solicitado no enunciado.

## 7. Capturas e respostas às perguntas do enunciado

### 7.1 DHCP: comunicação, mensagens e IPs

Arquivo: `wireshark/dhcp.pcapng`. A coleta na LAN do gateway acompanhou o reinício do cliente e contém o ciclo DORA:

| Quadro | IP de origem | IP de destino | Mensagem |
| --- | --- | --- | --- |
{dhcp_table}

O Discover parte de um cliente sem IPv4 configurado e é enviado em broadcast. O ACK confirma o lease e as opções de máscara, gateway, DNS e domínio; o detalhamento está em `evidencias/v1.0.0/dhcp-ack.txt`. Quadros adicionais, como Release, são preservados na captura.

### 7.2 DNS: nome consultado e servidor respondente

Arquivo: `wireshark/dns.pcapng`. No quadro **{dns_query[0]}**, `{dns_query[1]}` consultou **`{dns_query[3]}`**. No quadro **{dns_reply[0]}**, o servidor **`{dns_reply[1]}`** respondeu ao cliente. A captura também inclui consulta MX sobre TCP. Campos reais em `evidencias/v1.0.0/analise-dns.txt`.

### 7.3 HTTP: estabelecimento TCP, GET e URL

Arquivo: `wireshark/http.pcapng`. O cliente iniciou o fluxo TCP com SYN no quadro **{http['quadros']['SYN']}**; o servidor respondeu SYN/ACK em **{http['quadros']['SYN_ACK']}**; o ACK **{http['quadros']['ACK']}** concluiu o handshake. O quadro **{http['quadros']['GET']}** contém `GET /` e `Host: www.cardeal.local`; o servidor respondeu HTTP 200 no quadro **{http['quadros']['HTTP_200']}**.

A URL completa reconstruída do esquema HTTP, campo Host e caminho é **`{http['url']}`**. Campos em `evidencias/v1.0.0/analise-http.txt`.

### 7.4 E-mail: iniciador e comunicação dos protocolos

Arquivo: `wireshark/email.pcapng`. **O cliente `{mail['cliente_iniciador_tcp']}` iniciou a conexão TCP SMTP**, com SYN no quadro **{mail['quadros']['SYN_SMTP']}**. O servidor `{mail['servidor']}` enviou o banner SMTP 220 no quadro **{mail['quadros']['banner_220']}**. O primeiro texto de aplicação é esse banner do servidor; a abertura da conexão TCP foi iniciativa do cliente.

O cliente executou EHLO no quadro **{mail['quadros']['EHLO']}**, MAIL FROM em **{mail['quadros']['MAIL']}**, RCPT TO em **{mail['quadros']['RCPT']}** e DATA em **{mail['quadros']['DATA']}**. O servidor confirmou o enfileiramento com resposta 250. A mesma captura contém a autenticação, pesquisa e leitura IMAP; o FETCH está identificado no quadro **{mail['quadros']['FETCH_IMAP']}**. O teste confere a mensagem lida, e não apenas a aceitação SMTP. Campos e resumo em `evidencias/v1.0.0/analise-email.txt` e `email.json`.

Filtros de exibição úteis no Wireshark: `dhcp`, `dns`, `http`, `smtp`, `imap` e `tcp.flags.syn == 1`. As capturas foram feitas nos convidados; os fluxos cliente–servidor são coletados no cliente porque não atravessam o gateway. As quatro foram abertas no Wireshark real com plataforma gráfica offscreen, e a quantidade de quadros lida foi comparada ao TShark; registro em `evidencias/v1.0.0/verificacao-wireshark.txt`.

## 8. Persistência, falhas e reconstrução

O teste de persistência inventaria arquivos SMB e as mensagens reais em Maildir/cur e Maildir/new, comparando SHA-256, tamanho, UID/GID e modos antes de repetir qualquer transferência ou envio. Índices/cache do Dovecot e renomeações legítimas de flags são tratados como metadados operacionais; o conteúdo das mensagens é preservado. Após o teste de reinício, um novo inventário serve de base à reaplicação, pois o aceite intermediário envia mensagens novas. Os inventários de cada par são iguais.

O teste sem WAN desconecta apenas o primeiro cabo virtual do gateway, executa as funções internas e restaura esse cabo. O teste sem gateway desliga apenas a VM gateway, confirma os serviços LAN e a indisponibilidade externa, depois a religa. O teste do detector para Apache temporariamente e exige um resultado negativo verdadeiro, seguido de recuperação. As rotinas usam restauração em `finally` para recuperar o laboratório após o teste.

`./lab.sh reconstruir` criou `cardeal-r3-gw`, `cardeal-r3-srv` e `cardeal-r3-cli` a partir do disco Debian base não provisionado, usando LAN separada `cardeal-r3-validacao`, diretório `vms/reconstrucao-r3/` e portas SSH 2232–2234. As VMs originais ficaram desligadas durante essa validação para limitar a RAM e foram novamente disponibilizadas depois. Nenhum disco de convidado já configurado foi reutilizado como base. Instalação, serviços, topologia final e aceite após reinício passaram nas três VMs novas; os registros completos ficam em `evidencias/v1.0.0/reconstrucao/`.

Não restou instalação manual do sistema operacional: imagem oficial e NoCloud automatizam essa etapa. A preparação administrativa do hospedeiro, caso ainda necessária em outra máquina, segue o README e requer privilégios para instalar o VirtualBox e suas dependências. Backup privado dos dados anteriores à Sprint 3 foi mantido em `backups/antes-sprint3/`, fora da entrega e do Git.

## 9. Decisões e dificuldades resolvidas

1. **Memória disponível:** três Debian sem desktop e aplicações agrupadas no servidor mantêm a execução dentro dos recursos medidos. A reconstrução usa as mesmas dimensões, sem manter seis VMs ligadas ao mesmo tempo.
2. **Isolamento:** rede interna e NAT somente no gateway permitem estudar DHCP e roteamento preservando a conexão do Ubuntu. Não há publicação Web/SMB/SMTP/IMAP na interface física.
3. **Dovecot 2.4:** a sintaxe atual foi aplicada explicitamente e o passwd-file usa hashes de demonstração, UID/GID e home corretos; a conta Unix continua sem shell interativo.
4. **Identificador de mensagem no swaks:** a primeira tentativa anexou `Message-ID` além do campo automático `Message-Id`. O teste detectou a divergência. A configuração passou a substituir o cabeçalho com a grafia usada pelo swaks e exige exatamente um Message-ID, confirmado por IMAP.
5. **Capturas e AppArmor:** a análise usa cópias temporárias permitidas pelo perfil do TShark, preservando a política do sistema. Campos IMAP são tratados como texto conforme a versão instalada, e flags TCP como booleanos.
6. **Prontidão e acesso SSH:** a automação aguarda serviços funcionais após boot; usa configuração SSH relativa por causa dos espaços no caminho do projeto, conforme resolvido na R1.
7. **Reaplicação e dados:** diretórios de dados não são apagados, contas não são duplicadas e pacotes já instalados não exigem novos downloads. A comparação de dados ocorre antes dos testes que geram novos arquivos/mensagens.

## 10. Versões instaladas

| Máquina | Pacote | Versão registrada |
| --- | --- | --- |
{packages}

Kernel, memória, swap, discos, NICs e amostra do hospedeiro constam nos inventários de recursos e `vmstat-host.txt`. Os resultados demonstram a execução acadêmica atual; a quantidade configurada de leases não representa teste de carga de 101 clientes.

## 11. Operação, scripts e arquivos entregues

No Ubuntu, na raiz do projeto:

```bash
./lab.sh iniciar
./lab.sh cliente
# No terminal do cliente: ./lab.sh testar ; exit
./lab.sh testar
./lab.sh capturar
./lab.sh analisar
./lab.sh testar-persistencia
./lab.sh testar-sem-wan
./lab.sh testar-falha
./lab.sh testar-detector
```

Para criar a base em uma máquina preparada, usar `./lab.sh preparar`; para aplicar a versão atual nas VMs existentes, `./lab.sh atualizar`. A reconstrução de validação foi feita com `./lab.sh reconstruir`.

Os scripts estão em `src/host/`, `src/gateway/`, `src/servidor/`, `src/cliente/` e `src/testes/`; os templates ficam em `templates/`. A reprodução do documento usa `python3 src/host/compilar-relatorio.py`, `python3 src/host/gerar-relatorio.py` e `python3 src/host/empacotar.py`. Pandoc gera HTML autocontido; o Firefox gera PDF em perfil temporário exclusivo. O Git contém Markdown, diagramas, quatro pcapng, configurações, testes e evidências. HTML/PDF e o pacote são exportações locais ignoradas pelo Git; o PDF de especificação não é incluído no pacote.

O pacote é `entrega/cardeal-v1.0.0.tar.gz`; seus hashes e os dos principais artefatos ficam em `entrega/SHA256SUMS`. Credenciais privadas, discos, seeds e metadados locais não entram no pacote. O correio fictício público é incluído para permitir a demonstração dos protocolos conforme o enunciado.

**Resultado final:** requisitos funcionais, capturas, explicações, falhas, persistência e reconstrução aprovados nas execuções registradas. A publicação pode ser conferida no histórico Git; gerar o relatório não executa commit ou push.
'''
R.mkdir(parents=True, exist_ok=True)
(R/'relatorio.md').write_text(report)
print('Relatório final compilado com evidências verificadas:', R/'relatorio.md')
