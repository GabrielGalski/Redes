#!/usr/bin/env bash
# Funções compartilhadas; carregar com source a partir de um script Bash.

die() {
    printf 'ERRO: %s\n' "$*" >&2
    exit 1
}

load_packages() {
    local manifest line
    PACKAGES=()
    for manifest in "$@"; do
        [[ -r "$manifest" ]] || die "Manifesto indisponível: $manifest"
        while IFS= read -r line || [[ -n "$line" ]]; do
            line=${line%%#*}
            [[ "$line" =~ ^[[:space:]]*$ ]] && continue
            [[ "$line" =~ ^[a-z0-9][a-z0-9+.-]*$ ]] || die "Nome de pacote inválido em $manifest"
            PACKAGES+=("$line")
        done < "$manifest"
    done
    ((${#PACKAGES[@]} > 0)) || die 'Nenhum pacote definido.'
    mapfile -t PACKAGES < <(printf '%s\n' "${PACKAGES[@]}" | sort -u)
}

package_installed() {
    [[ $(dpkg-query -W -f='${db:Status-Status}' "$1" 2>/dev/null) == installed ]]
}

check_packages() {
    local package version
    MISSING_PACKAGES=()
    for package in "${PACKAGES[@]}"; do
        if package_installed "$package"; then
            version=$(dpkg-query -W -f='${Version}' "$package")
            printf 'OK       %-38s %s\n' "$package" "$version"
        else
            printf 'PENDENTE %s\n' "$package"
            MISSING_PACKAGES+=("$package")
        fi
    done
}

check_candidates() {
    local package candidate
    for package in "${PACKAGES[@]}"; do
        candidate=$(LC_ALL=C apt-cache policy "$package" | awk '/Candidate:/ {print $2; exit}')
        [[ -n "$candidate" && "$candidate" != '(none)' ]] || die "Sem candidato APT para $package. Confira os repositórios da distribuição."
    done
}
