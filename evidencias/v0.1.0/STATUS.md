# Aceite de rede — v0.1.0

**Estado: APROVADA em 05/11/2026 — versão funcional local `0.1.0`.**

O laboratório foi criado, configurado, desligado, iniciado novamente e testado nas três VMs reais. Gateway, servidor e cliente ficaram ligados ao final da validação.

| Critério | Resultado e evidência |
| --- | --- |
| Iniciar a partir das VMs desligadas | Aprovado: [início do laboratório](../../logs/rede/inicio-cliente.log). |
| Abrir o terminal do cliente com `./lab.sh cliente` | Aprovado: hostname `cardeal-cli`, IP da LAN e consulta interna em [terminal-cliente.txt](../../logs/rede/terminal-cliente.txt). |
| Receber IP/máscara/gateway/DNS/domínio por DHCP | `192.168.50.100/24`, gateway `.1`, DNS `.10`, `cardeal.local`: [ACK DHCP real](dhcp-ack.txt). |
| Resolver DNS interno/externo, A/MX/PTR e DNS por TCP | Aprovado: [teste funcional](teste-rede.txt). |
| Acessar HTTPS pelo gateway | Aprovado, HTTP 200 de `https://deb.debian.org/debian/`: [aceite final](../../logs/rede/aceite-final.log). |
| Cliente/servidor sem NAT próprio | Somente NIC LAN, segunda NIC `none`: [cliente](virtualbox-cliente.txt), [servidor](virtualbox-servidor.txt). |
| Persistir as funções após reinício | Aprovado: [reinício e repetição dos testes](../../logs/rede/reinicio.log). |
| Perder a saída externa sem gateway e recuperá-la ao religar | Aprovado; DNS interno permaneceu disponível: [teste de falha](teste-falha-gateway.txt). |
| Capturar DHCP DORA e DNS consulta/resposta | Aprovado: [análise DHCP](analise-dhcp.txt), [análise DNS](analise-dns.txt), [execução completa](../../logs/rede/capturas-final.log). |
| Preservar a conexão do hospedeiro | Comparação idêntica de interfaces, endereços estáveis, rotas IPv4 e resolv.conf: [registro](rede-hospedeiro.json). |
| Verificar dependências e recursos | Instalador/verificador retorna 0: [host](dependencias-host.txt); recursos de [gateway](recursos-gateway.txt), [servidor](recursos-servidor.txt), [cliente](recursos-cliente.txt). |

Capturas: [dhcp.pcapng](../../wireshark/dhcp.pcapng) e [dns.pcapng](../../wireshark/dns.pcapng). Imagem: [origem e SHA-512 verificado](imagem-debian.json). Explicação da montagem, dos pacotes e das dificuldades resolvidas: [relatório](../../logs/rede/RELATORIO.md).

Este registro cobre DHCP, DNS e gateway. Os aceites de Web, SMB e correio estão reunidos na [validação completa](../v1.0.0/STATUS.md).

## Testes dentro do cliente

O diretório inicial do usuário agora contém `lab.sh`, com `testar`, `status` e ajuda. O comando global `cardeal-lab` oferece as mesmas funções. O teste exato `./lab.sh testar` foi executado depois de entrar pela interface `./lab.sh cliente` e retornou aprovado: [registro](../../logs/rede/teste-atalho-cliente.txt).

Os comandos de administração das VMs continuam no terminal Ubuntu. O README e a mensagem de entrada no cliente identificam essa troca de contexto. O atalho foi instalado na VM ligada, preservando a sessão e as configurações de rede existentes.
