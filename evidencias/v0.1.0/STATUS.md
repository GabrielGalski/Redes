# Rodada 1 — v0.1.0

**Estado: APROVADA em 05/11/2026 — versão funcional local `0.1.0`.**

O laboratório foi criado, configurado, desligado, iniciado novamente e testado nas três VMs reais. Gateway, servidor e cliente ficaram ligados ao final da rodada.

| Critério | Resultado e evidência |
| --- | --- |
| Iniciar a partir das VMs desligadas | Aprovado: [início do laboratório](../../logs/rodada-1/inicio-cliente.log). |
| Abrir o terminal do cliente com `./lab.sh cliente` | Aprovado: hostname `cardeal-cli`, IP da LAN e consulta interna em [terminal-cliente.txt](../../logs/rodada-1/terminal-cliente.txt). |
| Receber IP/máscara/gateway/DNS/domínio por DHCP | `192.168.50.100/24`, gateway `.1`, DNS `.10`, `cardeal.local`: [ACK DHCP real](dhcp-ack.txt). |
| Resolver DNS interno/externo, A/MX/PTR e DNS por TCP | Aprovado: [teste funcional](teste-rede.txt). |
| Acessar HTTPS pelo gateway | Aprovado, HTTP 200 de `https://deb.debian.org/debian/`: [aceite final](../../logs/rodada-1/aceite-final.log). |
| Cliente/servidor sem NAT próprio | Somente NIC LAN, segunda NIC `none`: [cliente](virtualbox-cliente.txt), [servidor](virtualbox-servidor.txt). |
| Persistir as funções após reinício | Aprovado: [reinício e repetição dos testes](../../logs/rodada-1/reinicio.log). |
| Perder a saída externa sem gateway e recuperá-la ao religar | Aprovado; DNS interno permaneceu disponível: [teste de falha](teste-falha-gateway.txt). |
| Capturar DHCP DORA e DNS consulta/resposta | Aprovado: [análise DHCP](analise-dhcp.txt), [análise DNS](analise-dns.txt), [execução completa](../../logs/rodada-1/capturas-final.log). |
| Preservar a conexão do hospedeiro | Comparação idêntica de interfaces, endereços estáveis, rotas IPv4 e resolv.conf: [registro](rede-hospedeiro.json). |
| Verificar dependências e recursos | Instalador/verificador retorna 0: [host](dependencias-host.txt); recursos de [gateway](recursos-gateway.txt), [servidor](recursos-servidor.txt), [cliente](recursos-cliente.txt). |

Capturas: [dhcp.pcapng](../../wireshark/dhcp.pcapng) e [dns.pcapng](../../wireshark/dns.pcapng). Imagem: [origem e SHA-512 verificado](imagem-debian.json). Explicação da montagem, dos pacotes e das dificuldades resolvidas: [relatório](../../logs/rodada-1/RELATORIO.md).

Próxima entrega: Sprint 2, com Web e SMB sobre a rede básica validada. Nesta rodada, `www`, `mail` e `files` são registros DNS que preparam os próximos serviços.

## Testes dentro do cliente

O diretório inicial do usuário agora contém `lab.sh`, com `testar`, `status` e ajuda. O comando global `cardeal-lab` oferece as mesmas funções. O teste exato `./lab.sh testar` foi executado depois de entrar pela interface `./lab.sh cliente` e retornou aprovado: [registro](../../logs/rodada-1/teste-atalho-cliente.txt).

Os comandos de administração das VMs continuam no terminal Ubuntu. O README e a mensagem de entrada no cliente identificam essa troca de contexto. O atalho foi instalado na VM ligada, preservando a sessão e as configurações de rede existentes.
