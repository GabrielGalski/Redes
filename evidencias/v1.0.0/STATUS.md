# Entrega final — v1.0.0

**Estado: APROVADA localmente em 07/11/2026.** Os requisitos funcionais do enunciado e os critérios de aceite foram executados nas VMs reais, incluindo a reconstrução em três convidados novos. Gateway, servidor e cliente originais ficaram ligados; as VMs de validação ficaram desligadas.

**Revalidação completa aprovada em 20/11/2026:** [registro atual](verificacao/STATUS.md), incluindo preservação dos dados, reinício, reaplicação, reconstrução, falhas controladas e quatro capturas.

## Critérios de aceite

| Critério | Resultado e evidência |
| --- | --- |
| Conservar as duas versões anteriores | Rede, DNS, HTTPS externo, HTTP e SMB aprovados no [teste integrado](teste-integrado.txt) e no [terminal real do cliente](../../logs/laboratorio/terminal-cliente.txt). |
| Ana e Bruno enviam e leem mensagens nos dois sentidos | Swaks confirmou as filas SMTP; curl leu por IMAP e comparou Message-ID, remetente, destinatário e corpo: [teste](teste-email.txt), [mensagens capturadas](mensagens-capturadas.json) e [log de entrega Postfix](log-postfix.txt). |
| Recusar destinatário inexistente e relay externo da LAN | SMTP `550 5.1.1` e `554 5.7.1`, respectivamente: [teste](teste-email.txt) e [Postfix](log-postfix.txt). |
| Configuração Postfix/Dovecot válida e compatível | `postfix check`, `postconf -n`, `doveconf -n`, serviços, portas, Apache, Samba e nftables aprovados: [validadores](validadores-servidor.txt). Dovecot instalado: 2.4.1. |
| Identificar comunicação SMTP e leitura IMAP na captura | [email.pcapng](../../wireshark/email.pcapng), [resumo de quadros](email.json) e [campos extraídos](analise-email.txt): iniciador TCP, banner, EHLO/MAIL/RCPT/DATA e FETCH IMAP. |
| Manter DNS/Web/SMB/e-mail sem WAN e recuperar gateway | [LAN sem WAN](teste-sem-wan.txt); [gateway desligado e religado](teste-falha-gateway.txt); baterias integradas aprovadas após recuperação. |
| Preservar serviços e dados após reinício | [Inventário anterior](inventario-antes.json) igual ao [posterior](inventario-pos-reinicio.json), com arquivos e mensagens Maildir; [execução](../../logs/laboratorio/persistencia.log). Recursos medidos com os serviços ativos. |
| Reaplicação preserva dados e reconstrução é comprovada | [Antes da reaplicação](inventario-antes-reaplicacao.json) igual ao [depois](inventario-pos-reaplicacao.json); [resultado](persistencia.json). [Reconstrução aprovada](reconstrucao.json), [preparação das VMs novas](reconstrucao/preparacao.log) e [aceite após seu reinício](reconstrucao/reinicio.log). |
| Verificador reprova serviço indisponível e aprova recuperação | Apache parado intencionalmente: [resultado negativo](detector-servico-parado.txt); [resumo](detector.json) e [execução](../../logs/laboratorio/detector.log). |
| Quatro capturas abrem no Wireshark e respondem ao PDF | Abertura pelo Wireshark real em modo gráfico offscreen e contagens comparadas com TShark: [verificação](verificacao-wireshark.txt). Relatório identifica os quadros e responde a cada pergunta. |
| Scripts, templates, versões e relatório organizados | [README](../../README.md), [fontes](../../src/), [templates](../../templates/), [topologia](../../topologia/topologia.svg) e [relatório final](../../logs/relatorio/relatorio.md). HTML/PDF e pacote `entrega/cardeal-v1.0.0.tar.gz` são exportações locais ignoradas pelo Git. |

## Respostas às capturas exigidas no enunciado

| Captura | Resposta obtida |
| --- | --- |
| DHCP | DORA com IPs de origem/destino em [analise-dhcp.txt](analise-dhcp.txt); opções em [dhcp-ack.txt](dhcp-ack.txt). |
| DNS | Consulta `www.cardeal.local` e resposta do servidor `192.168.50.10`, em [analise-dns.txt](analise-dns.txt). |
| HTTP | Handshake TCP, GET e Host; URL reconstruída `http://www.cardeal.local/`, em [http.json](http.json). |
| E-mail | O cliente `192.168.50.100` iniciou o TCP SMTP; o servidor `.10` enviou o banner 220. Comandos SMTP e leitura IMAP identificados em [email.json](email.json). |

Capturas canônicas: [DHCP](../../wireshark/dhcp.pcapng), [DNS](../../wireshark/dns.pcapng), [HTTP](../../wireshark/http.pcapng) e [SMTP/IMAP](../../wireshark/email.pcapng). A autenticação IMAP capturada é fictícia e pública, definida em [email-demo.json](../../config/email-demo.json), distinta das credenciais SMB privadas.

## Ambiente e reprodução

- [Imagem Debian e SHA-512](imagem-debian.json), verificados na reconstrução.
- Recursos e versões de [gateway](recursos-gateway.txt), [servidor](recursos-servidor.txt), [cliente](recursos-cliente.txt) e [hospedeiro](recursos-hospedeiro.txt); inventários completos em `pacotes-*.txt`.
- [Amostra do hospedeiro](vmstat-host.txt) e [preservação da rede](rede-hospedeiro.json).
- [Validação dos scripts e dependências](validacao-codigo.txt).
- A reconstrução usa VMs e LAN independentes, com portas locais 2232–2234; as originais permanecem preservadas. A instalação do SO usa NoCloud e não exige passos manuais. A preparação administrativa do hospedeiro em outra máquina está documentada no README.
- Dados existentes foram copiados para backup privado, fora do Git e do pacote. Discos, seeds, chaves e senhas SMB não acompanham a entrega.

Comandos principais: `./lab.sh iniciar`, `./lab.sh cliente` e `./lab.sh testar`. Dentro do cliente, `./lab.sh testar` apresenta o resultado de rede, intranet e e-mail. Os testes com falhas e reconstrução estão documentados no README e no relatório.

Os registros iniciais são de 07/11/2026; a reconstrução e a verificação atual são de 20/11/2026. Os commits publicados podem ser conferidos no histórico Git; PDFs, pacotes e arquivos privados permanecem locais.
