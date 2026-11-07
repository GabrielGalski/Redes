# Cardeal Ltda — trabalho de Redes de Computadores

Planejamento baseado em [Trabalho Infraestrutura.pdf](Trabalho%20Infraestrutura.pdf).

- [Plano de implementação](docs/PLANO_DE_IMPLEMENTACAO.md): requisitos, topologia, endereçamento, sequência de execução, testes, capturas e entregas.
- [Plano de sprints](sprints.md): três entregas funcionais cumulativas, versões, tarefas e critérios de aceite.
- [Ferramentas e gratuidade](docs/FERRAMENTAS.md): inventário completo da stack escolhida, pacotes, instalação por máquina, licenças e compatibilidade.
- [Requisitos de sistema](requirements.txt): ferramentas e pacotes agrupados por hospedeiro e VM, incluindo os componentes da instalação base.
- [Configuração de exemplo](config/lab.env.example): parâmetros de rede, recursos e acesso administrativo previstos.
- [Preparação do ambiente](docs/PREPARACAO_DO_AMBIENTE.md): instalação, simulação e verificação das dependências do hospedeiro e das VMs.

Estado em **05/11/2026**: **v0.1.0 implementada e validada nas três VMs reais**, que ficaram ligadas ao final da entrega. Consulte o [estado de aceite da rodada 1](evidencias/v0.1.0/STATUS.md) e o [relatório da rodada](logs/rodada-1/RELATORIO.md). O registro em `evidencias/ambiente/` preserva o histórico da preparação anterior.

A proposta usa **VirtualBox + três VMs Debian 13 sem interface gráfica**, executadas no Ubuntu 26.04 LTS atual. O conjunto atende ao laboratório local sem serviços pagos, assinatura, cartão de crédito ou cotas de SaaS. A RAM das VMs precisa ser validada com os serviços em execução.

## Executar a primeira rodada

A rodada entrega DHCP, DNS interno/externo, gateway/NAT e cliente Debian acessível por terminal SSH. Os nomes `www`, `files` e `mail` já resolvem; os serviços Web, SMB e e-mail serão entregues nas próximas sprints.

Na raiz do projeto, como usuário normal do Ubuntu:

```bash
./lab.sh preparar      # primeira vez: baixar/verificar imagem, criar e provisionar
./lab.sh iniciar       # iniciar as três VMs já preparadas
./lab.sh cliente       # abrir o terminal do cliente pela LAN, via gateway
```

Depois de `./lab.sh cliente`, o prompt `cardeal@cardeal-cli:~$` indica que você está **dentro da VM Debian**. Nesse terminal:

```bash
./lab.sh testar       # verificar as funções de rede a partir do cliente
./lab.sh status       # endereços e rotas do cliente
ip -br address
ip route
getent hosts www.cardeal.local
dig @192.168.50.10 cardeal.local MX
curl -I https://deb.debian.org/debian/
exit
```

O atalho `cardeal-lab testar` também funciona em qualquer diretório da VM. O teste local verifica DHCP, DNS e acesso externo. Para a verificação adicional das NICs VirtualBox e da rede do hospedeiro, use o comando de testes no Ubuntu.

**No terminal Ubuntu, na pasta do projeto**, execute a administração das VMs e os testes completos. Se estiver no prompt do cliente, digite `exit` primeiro:

```bash
./lab.sh status        # estado das VMs e IP atual do cliente
./lab.sh testar        # aceite funcional e conferência da rede do hospedeiro
./lab.sh reiniciar     # reiniciar as VMs e repetir o aceite
./lab.sh capturar      # DHCP DORA e consulta/resposta DNS
./lab.sh analisar      # analisar novamente as capturas existentes
./lab.sh testar-falha  # desligar só o gateway virtual, testar e religá-lo
./lab.sh parar         # desligamento ACPI somente das VMs do projeto
```

A imagem oficial Debian e seu SHA-512 estão fixados em [config/debian-image.json](config/debian-image.json). NoCloud configura os convidados por uma pequena ISO local de dados. A automação usa Python 3 da distribuição, xorriso, xz-utils, OpenSSL, curl, SSH e VirtualBox, sem dependências pip nem serviços de nuvem.

Discos, seeds, catálogo VirtualBox e chaves exclusivas ficam em `vms/`, ignorado pelo Git. `lab.sh` seleciona esse catálogo próprio, em vez do catálogo padrão do VirtualBox. O usuário SSH é `cardeal` por padrão; a credencial para uma eventual sessão pelo console está no arquivo local privado `vms/.runtime/acesso-console.json`, sem entrar no Git.

Somente o gateway mantém NAT depois do bootstrap. O SSH fica vinculado a `127.0.0.1:2222` no hospedeiro. A criação não configura bridge, host-only, rotas, DNS, firewall ou interfaces físicas do Ubuntu. A automação registra e compara a rede do hospedeiro antes/depois.

## Estrutura do repositório

```text
.
├── README.md
├── lab.sh                    # criar, iniciar, acessar e verificar o laboratório
├── VERSION                   # versão funcional validada
├── sprints.md                # evolução funcional em três versões
├── requirements.txt          # inventário de ferramentas e pacotes de sistema
├── .gitignore
├── Trabalho Infraestrutura.pdf
├── config/
│   ├── lab.env.example       # parâmetros de referência, sem senhas
│   └── packages/             # manifestos APT por máquina
├── docs/                     # planejamento e ferramentas
├── src/
│   ├── common/               # funções de leitura/verificação de pacotes
│   ├── instalar-dependencias-vm.sh
│   ├── host/                 # preparação do hospedeiro, VMs e SSH
│   ├── gateway/              # rede, NAT, firewall e DHCP
│   ├── servidor/             # DNS, Web, SMB e e-mail
│   ├── cliente/              # DHCP, resolução e utilitários
│   └── testes/               # verificações e coleta de evidências
├── templates/
│   ├── networkd/
│   ├── gateway/
│   ├── dhcp/
│   ├── dns/
│   ├── web/
│   ├── smb/
│   └── email/
├── topologia/                # fonte DOT e diagramas gerados
├── wireshark/                # capturas pcapng
├── evidencias/               # logs, resultados e inventários
└── logs/                     # execução e relatório da rodada
```

Os diretórios reservados contêm `.gitkeep` para serem preservados no Git. A primeira rodada adiciona orquestração em `src/host/lab.py`, configuração dos convidados em `src/gateway/`, `src/servidor/` e `src/cliente/`, templates e testes funcionais em `src/testes/`. `docs/` e `sprints.md` permanecem ignorados pelo Git.

O `requirements.txt` contém dependências de sistema organizadas por máquina; sua instalação será feita pelos respectivos gerenciadores de pacotes. Bibliotecas transitivas serão resolvidas pelo APT. A configuração local está em `config/lab.env`, ignorada pelo Git.

## Preparar o hospedeiro

Na raiz do projeto, executar:

```bash
bash src/host/preparar-ambiente.sh --plan
sudo bash src/host/preparar-ambiente.sh --install
bash src/host/preparar-ambiente.sh --check
```

As dependências das VMs são instaladas separadamente, dentro de cada convidado Debian 13. Os detalhes estão no [guia de preparação](docs/PREPARACAO_DO_AMBIENTE.md).
