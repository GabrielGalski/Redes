# Validação do laboratório

**Resultado: APROVADO em 20/11/2026**, com três VMs Debian 13 no Ubuntu 26.04.

| Verificação | Resultado e registro |
| --- | --- |
| Rede, DNS, internet, Web, SMB e correio | Aceite integrado aprovado: [teste](teste-integrado.txt) e [terminal do cliente](cliente.log). |
| Atualização preserva arquivos, mensagens, contas e permissões | Inventários [antes](inventario-antes-atualizacao.json) e [depois](inventario-depois-atualizacao.json) iguais, antes de gerar novos dados de teste. |
| Reinício e reaplicação | [Persistência aprovada](persistencia.json), com inventários e [execução](persistencia.log). |
| Serviço parado é detectado e restaurado | [Apache](detector.json): reprovação intencional, seguida de recuperação aprovada. |
| Serviços internos sem WAN e sem gateway | [WAN virtual desconectada](teste-sem-wan.txt) e [gateway desligado](teste-falha-gateway.txt); recuperação aprovada. |
| Reconstrução completa | [VMs novas](../reconstrucao.json), com [preparação](../reconstrucao/preparacao.log) e [aceite após reinício](../reconstrucao/reinicio.log). |
| DHCP, DNS, HTTP e SMTP/IMAP | [Quatro capturas atuais](wireshark/), [análise](analise.log) e [abertura no Wireshark](verificacao-wireshark.txt) aprovadas. As capturas históricas da raiz foram preservadas. |
| Código aplicado nas três VMs | [Sincronização](sincronizacao.log): arquivos atuais instalados e dados preservados. |
| Rede do Ubuntu | [Comparação antes/depois](rede-hospedeiro.json) sem alterações. |
| Dependências do hospedeiro | [Verificação](dependencias.log) aprovada; manifestos por máquina preservados. |
| Código e comandos públicos | [Sintaxe, referências Python, ShellCheck e manifestos](validacao-codigo.txt) aprovados; 21 comandos preservados. |

Os 21 comandos públicos de `lab.sh` permanecem disponíveis. Os scripts de configuração usam nomes de função: rede, intranet e e-mail. As capturas contêm somente as credenciais fictícias públicas de IMAP usadas na demonstração.
