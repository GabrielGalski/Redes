# Estado da preparação — 01/11/2026

> Registro histórico. A preparação e a implementação da rede básica foram concluídas e validadas em 05/11/2026. Consulte o [estado atual da rodada 1](../v0.1.0/STATUS.md).

**Preparação parcial: instalação administrativa pendente.**

## Concluído

- Inventários APT separados por hospedeiro, base Debian e papel da VM.
- Instalador Ubuntu com modos de simulação, instalação e verificação.
- Instalador Debian que impede instalar serviços no hospedeiro e valida o papel da VM.
- Configuração local `config/lab.env` criada sem senhas e ignorada pelo Git.
- Scripts verificados com `bash -n` e ShellCheck 0.11.0, extraído em `/tmp` para a análise, sem instalação no sistema.
- Simulação APT executada com os repositórios locais; nenhuma remoção prevista.
- Bloqueio de execução do instalador de serviços no Ubuntu verificado: recusou antes de instalar.

## Pendências reais

VirtualBox, DKMS, Wireshark, TShark, ShellCheck, Pandoc e gawk ainda não estão instalados no hospedeiro. O driver `/dev/vboxdrv` não está disponível. Git, OpenSSH cliente, Graphviz, curl, ferramentas de compilação e headers do kernel já estavam instalados.

A instalação foi tentada com `sudo -n bash scripts/host/preparar-ambiente.sh --install`, fora da restrição inicial da sessão. O sistema respondeu `sudo: interactive authentication is required`; a execução não chegou ao APT. Não houve rejeição da revisão automática de aprovação: o impedimento foi a autenticação local do sudo.

Para concluir essa etapa, na raiz do projeto, executar em um terminal local:

```bash
sudo bash scripts/host/preparar-ambiente.sh --install
bash scripts/host/preparar-ambiente.sh --check
```

Depois será necessário criar/instalar as três VMs e executar o instalador de dependências de cada papel. Os serviços de rede ainda não foram configurados, iniciados ou testados.

## Evidências

- [Verificação dos pacotes e executáveis do hospedeiro](verificacao-host.txt).
- [Simulação APT](plano-apt.txt).
- [Validação dos scripts e manifestos](validacao.txt).

Esses arquivos registram o levantamento; a verificação deve ser repetida depois da instalação.
