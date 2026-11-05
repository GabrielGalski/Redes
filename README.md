# Cardeal Ltda — trabalho de Redes de Computadores

Planejamento baseado em [Trabalho Infraestrutura.pdf](Trabalho%20Infraestrutura.pdf).

- [Plano de implementação](docs/PLANO_DE_IMPLEMENTACAO.md): requisitos, topologia, endereçamento, sequência de execução, testes, capturas e entregas.
- [Plano de sprints](sprints.md): três entregas funcionais cumulativas, versões, tarefas e critérios de aceite.
- [Ferramentas e gratuidade](docs/FERRAMENTAS.md): inventário completo da stack escolhida, pacotes, instalação por máquina, licenças e compatibilidade.
- [Requisitos de sistema](requirements.txt): ferramentas e pacotes agrupados por hospedeiro e VM, incluindo os componentes da instalação base.
- [Configuração de exemplo](config/lab.env.example): parâmetros de rede, recursos e acesso administrativo previstos.
- [Preparação do ambiente](docs/PREPARACAO_DO_AMBIENTE.md): instalação, simulação e verificação das dependências do hospedeiro e das VMs.

Estado em **01/11/2026**: planejamento, estrutura, manifestos de pacotes e instaladores de dependências criados. A instalação administrativa no hospedeiro ficou pendente porque o `sudo` exige autenticação interativa. As VMs e os serviços ainda precisam ser implementados. Consulte o [estado do ambiente](evidencias/ambiente/STATUS.md).

A proposta usa **VirtualBox + três VMs Debian 13 sem interface gráfica**, executadas no Ubuntu 26.04 LTS atual. O conjunto atende ao laboratório local sem serviços pagos, assinatura, cartão de crédito ou cotas de SaaS. A RAM das VMs precisa ser validada com os serviços em execução.

## Estrutura do repositório

```text
.
├── README.md
├── sprints.md                # evolução funcional em três versões
├── requirements.txt          # inventário de ferramentas e pacotes de sistema
├── .gitignore
├── Trabalho Infraestrutura.pdf
├── config/
│   ├── lab.env.example       # parâmetros de referência, sem senhas
│   └── packages/             # manifestos APT por máquina
├── docs/                     # planejamento e ferramentas
├── scripts/
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
└── relatorio/                # relatório Markdown, HTML e PDF
```

Os diretórios reservados contêm `.gitkeep` para serem preservados no Git. Os instaladores de dependências já estão disponíveis; configurações de serviços, diagramas e capturas serão adicionados nas etapas de implementação.

O `requirements.txt` contém dependências de sistema organizadas por máquina; sua instalação será feita pelos respectivos gerenciadores de pacotes. Bibliotecas transitivas serão resolvidas pelo APT. A configuração local está em `config/lab.env`, ignorada pelo Git.

## Preparar o hospedeiro

Na raiz do projeto, executar:

```bash
bash scripts/host/preparar-ambiente.sh --plan
sudo bash scripts/host/preparar-ambiente.sh --install
bash scripts/host/preparar-ambiente.sh --check
```

As dependências das VMs são instaladas separadamente, dentro de cada convidado Debian 13. Os detalhes estão no [guia de preparação](docs/PREPARACAO_DO_AMBIENTE.md).
