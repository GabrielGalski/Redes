#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=src/common/guest.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../common/guest.sh"
guest_guard cliente
umask 077
WORK=$(mktemp -d /tmp/cardeal-intranet.XXXXXX)
trap 'rm -rf -- "$WORK"' EXIT
SHARE="//files.$LAB_DOMAIN/compartilhado"
SMB_OPTIONS=(-p 445 -m SMB3 --option='client min protocol=SMB2_02' --client-protection=sign -t 15)
ANA=/etc/cardeal/credentials/ana.auth
BRUNO=/etc/cardeal/credentials/bruno.auth
[[ -r "$ANA" && -r "$BRUNO" ]]
cd "$WORK"

echo '=== Intranet HTTP por nome DNS ==='
getent ahostsv4 "www.$LAB_DOMAIN" | grep -F "$LAB_SERVER_IP"
CODE=$(curl --noproxy '*' --http1.1 --silent --show-error --connect-timeout 10 --max-time 30 \
    -D cabecalhos.txt -o pagina.html -w '%{http_code}' "http://www.$LAB_DOMAIN/")
[[ "$CODE" == 200 ]] || { echo "HTTP inesperado: $CODE"; exit 1; }
grep -F 'data-app="cardeal-intranet"' pagina.html
grep -F 'Cardeal Ltda' pagina.html
curl --noproxy '*' --fail --silent --show-error --max-time 15 "http://www.$LAB_DOMAIN/estilo.css" -o estilo.css
[[ -s estilo.css ]]
cat cabecalhos.txt
echo 'OK: página Cardeal e CSS retornam HTTP 200 pelo nome.'

echo '=== Arquivo de Ana para Bruno por SMB autenticado ==='
getent ahostsv4 "files.$LAB_DOMAIN" | grep -F "$LAB_SERVER_IP"
printf 'Cardeal Ltda — aceite v0.2.0\nArquivo enviado por Ana e lido por Bruno.\n' > origem.txt
# Antes de escrever, conferir o arquivo de uma execução anterior, se existir.
if smbclient "$SHARE" "${SMB_OPTIONS[@]}" -A "$BRUNO" -c 'get aceite-cardeal/ana-para-bruno.txt anterior.txt' > anterior.log 2>&1; then
    cmp origem.txt anterior.txt
    echo 'OK: arquivo anterior permanece acessível e íntegro.'
else
    grep -F 'NT_STATUS_OBJECT_NAME_NOT_FOUND' anterior.log >/dev/null || { cat anterior.log; exit 1; }
    echo 'Primeira execução: arquivo de aceite ainda não existe.'
fi
smbclient "$SHARE" "${SMB_OPTIONS[@]}" -A "$ANA" -c 'put origem.txt aceite-cardeal/ana-para-bruno.txt'
smbclient "$SHARE" "${SMB_OPTIONS[@]}" -A "$BRUNO" -c 'get aceite-cardeal/ana-para-bruno.txt recebido.txt'
cmp origem.txt recebido.txt
sha256sum origem.txt recebido.txt
echo 'OK: Ana enviou, Bruno baixou e os hashes SHA-256 coincidem.'
# Bruno também precisa poder alterar um arquivo criado por Ana.
cp recebido.txt colaboracao.txt
smbclient "$SHARE" "${SMB_OPTIONS[@]}" -A "$BRUNO" -c 'put colaboracao.txt aceite-cardeal/ana-para-bruno.txt'
smbclient "$SHARE" "${SMB_OPTIONS[@]}" -A "$ANA" -c 'get aceite-cardeal/ana-para-bruno.txt retorno.txt'
cmp origem.txt retorno.txt
echo 'OK: ambos os funcionários têm leitura e escrita no mesmo arquivo.'

echo '=== Rejeição de credencial incorreta e acesso anônimo ==='
printf 'username = ana\npassword = senha-incorreta-para-teste\ndomain = CARDEAL\n' > incorreta.auth
if smbclient "$SHARE" "${SMB_OPTIONS[@]}" -A incorreta.auth -c ls > incorreta.log 2>&1; then
    echo 'ERRO: senha incorreta foi aceita.'; exit 1
fi
grep -F NT_STATUS_LOGON_FAILURE incorreta.log
if smbclient "$SHARE" "${SMB_OPTIONS[@]}" -N -U '%' -c ls > anonimo.log 2>&1; then
    echo 'ERRO: acesso anônimo foi aceito.'; exit 1
fi
grep -E 'NT_STATUS_(ACCESS_DENIED|LOGON_FAILURE)' anonimo.log
echo 'OK: Samba recusa senha incorreta e acesso sem autenticação.'
echo 'ACEITE FUNCIONAL DA INTRANET: APROVADO'
