#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $(cat /etc/cardeal-role 2>/dev/null) != cliente ]]; then
    printf 'Este atalho deve ser executado dentro da VM cliente.\n' >&2
    exit 1
fi

case "${1:-ajuda}" in
    testar)
        printf 'Ambiente: VM cliente. Verificando suas funções de rede...\n'
        exec sudo -n bash /opt/cardeal/src/testes/testar-rede.sh
        ;;
    status)
        hostname
        ip -br address
        ip route
        ;;
    ajuda|--help|-h)
        printf 'Você está na VM cliente.\n'
        printf '  ./lab.sh testar   Testar DHCP, DNS e acesso externo do cliente.\n'
        printf '  ./lab.sh status   Mostrar endereços e rotas do cliente.\n'
        printf '  exit              Retornar ao terminal Ubuntu.\n'
        printf 'O comando cardeal-lab oferece as mesmas opções em qualquer diretório.\n'
        ;;
    *)
        printf 'Esse comando deve ser executado na pasta do projeto no Ubuntu hospedeiro.\n' >&2
        printf 'Digite exit para sair da VM. Aqui, use ./lab.sh testar ou ./lab.sh status.\n' >&2
        exit 2
        ;;
esac
