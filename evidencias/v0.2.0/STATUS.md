# Rodada 2 — v0.2.0

**Estado: APROVADA localmente em 06/11/2026.** A segunda sprint foi implementada e validada nas três VMs existentes. Gateway, servidor e cliente permaneceram ligados ao final da entrega.

A Sprint 1 foi publicada antes desta implementação: commit [`de1cebb`](https://github.com/GabrielGalski/Redes/commit/de1cebb), mensagem `feat: DHCP, DNS e gateway`, enviado para `origin/main`. Esta entrega reúne a Sprint 2 e a documentação das VMs e da rede, com a mensagem de commit `feat: intranet Web e compartilhamento SMB`.

| Critério do plano | Resultado e evidência |
| --- | --- |
| Manter os testes da v0.1.0 aprovados | DHCP, DNS interno/externo UDP/TCP, MX/PTR, gateway e HTTPS: [teste de rede](teste-rede.txt). Perda e recuperação do gateway: [registro](teste-falha-gateway.txt). DHCP/DNS reanalisados: [execução](../../logs/rodada-2/analise-capturas.log). |
| HTTP 200 e conteúdo Cardeal pelo nome | Página `http://www.cardeal.local/` e CSS local aprovados: [teste da intranet](teste-intranet.txt). |
| Ana envia, Bruno baixa e SHA-256 coincide | Transferência de 73 bytes, comparação byte a byte e hash `69587c5d7772a6fdaf9c4bed465f3c18785e4e476c178c29764894df6241bb37`: [teste SMB](teste-intranet.txt). Bruno também escreve no arquivo criado por Ana. |
| Recusar credencial incorreta e acesso anônimo | `NT_STATUS_LOGON_FAILURE` e `NT_STATUS_ACCESS_DENIED`, respectivamente: [resultados](teste-intranet.txt). |
| Validar Apache e Samba | `apache2ctl configtest`: `Syntax OK`; `testparm`: configuração válida; nftables também validado: [validadores](validadores-servidor.txt). |
| Restaurar Web/SMB após reinício, preservando dados/permissões | Três VMs desligadas por ACPI e reiniciadas; serviços habilitados e funcionais. [Inventário anterior](inventario-antes.json) idêntico ao [posterior](inventario-pos-reinicio.json), comparado antes de nova transferência; [execução](../../logs/rodada-2/persistencia.log). |
| Capturar handshake, GET, Host e resposta HTTP | [http.pcapng](../../wireshark/http.pcapng): quadros 1/2/3 = SYN/SYN-ACK/ACK, 4 = GET/Host, 6 = HTTP 200. [Análise](analise-http.txt), [resumo](http.json) e [relatório com URL reconstruída](../../logs/rodada-2/RELATORIO.md). |
| Reaplicar sem duplicar contas nem apagar arquivos | [Inventário após reaplicação](inventario-pos-reaplicacao.json) idêntico ao anterior; contas únicas, SHA-256, UID/GID e modos preservados antes de repetir o teste: [resultado](persistencia.json). |

## Operação e preservação do hospedeiro

- O fluxo público `./lab.sh cliente` → `./lab.sh testar` executa rede **e** intranet dentro do cliente: [terminal real](../../logs/rodada-2/terminal-cliente.txt).
- No Ubuntu, `./lab.sh atualizar`, `./lab.sh testar-intranet`, `./lab.sh testar-persistencia` e `./lab.sh capturar-http` compõem a nova entrega. `./lab.sh testar` é cumulativo.
- A configuração da rede do hospedeiro permaneceu igual: [hashes antes/depois](rede-hospedeiro.json). A instalação e as regras de serviços/firewall desta rodada ocorreram nos convidados.
- Cliente e servidor permanecem com uma única NIC interna: [cliente](virtualbox-cliente.txt) e [servidor](virtualbox-servidor.txt). Somente o [gateway](virtualbox-gateway.txt) tem WAN NAT; não foram publicados Web/SMB na rede do Ubuntu.
- Memória, swap, discos e versões foram medidos: [gateway](recursos-gateway.txt), [servidor](recursos-servidor.txt), [cliente](recursos-cliente.txt), [amostra do hospedeiro](vmstat-host.txt). As três VMs apresentaram uso de swap zero na medição.
- Python, Bash, ShellCheck e manifestos de dependências foram conferidos: [validação](validacao-codigo.txt). Não há novas dependências no hospedeiro para a R2.
- Credenciais aleatórias ficam em `secrets/` e em arquivos protegidos nos convidados, sem entrar no Git ou nos resultados. Scripts de aplicação: [servidor](../../src/servidor/configurar-r2.sh) e [cliente](../../src/cliente/configurar-r2.sh).

Documentação: [README](../../README.md), [relatório da rodada](../../logs/rodada-2/RELATORIO.md), [relatório parcial consolidado](../../logs/relatorio/relatorio.md) e [topologia](../../topologia/topologia.svg). Próxima etapa: Sprint 3, com correio interno e reconstrução integrada.
