#!/usr/bin/env bash
# scripts/share_dashboard.sh
#
# Sobe Streamlit + Caddy (reverse proxy) + Cloudflare Tunnel e imprime a URL
# publica HTTPS para compartilhar o dashboard com a coordenacao.
#
# Uso:
#   ./scripts/share_dashboard.sh up        # sobe a stack e imprime URL publica
#   ./scripts/share_dashboard.sh url       # reimprime a URL do tunel ativo
#   ./scripts/share_dashboard.sh logs      # stream de logs
#   ./scripts/share_dashboard.sh status    # diagnostico rapido (health + endpoints)
#   ./scripts/share_dashboard.sh rebuild   # forca reconstrucao da imagem Streamlit
#   ./scripts/share_dashboard.sh down      # derruba tudo
#
# Requer: docker + docker compose plugin.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/infra/docker-compose.share.yml"
PROJECT="enel-share"

DC=(docker compose -p "${PROJECT}" -f "${COMPOSE_FILE}")

ok()   { printf '\033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '\033[33m⚠\033[0m %s\n' "$*"; }
err()  { printf '\033[31m✗\033[0m %s\n' "$*"; }
step() { printf '\033[36m→\033[0m %s\n' "$*"; }

wait_streamlit_healthy() {
    step "Aguardando Streamlit ficar saudavel (pode levar ate 90s no primeiro build)..."
    local status=""
    for i in $(seq 1 60); do
        sleep 3
        status="$(docker inspect -f '{{.State.Health.Status}}' enel-streamlit 2>/dev/null || echo missing)"
        if [[ "${status}" == "healthy" ]]; then
            ok "Streamlit healthy"
            return 0
        fi
        if (( i % 5 == 0 )); then
            printf '   ...(%ds) status=%s\n' "$((i*3))" "${status}"
        fi
    done
    err "Streamlit nao ficou healthy. Rode: $0 logs"
    return 1
}

wait_local_ready() {
    step "Validando proxy local em http://localhost:8080 ..."
    for i in $(seq 1 30); do
        if curl -fsS -o /dev/null http://localhost:8080/_stcore/health 2>/dev/null \
           || curl -fsS -o /dev/null http://localhost:8080/ 2>/dev/null; then
            ok "Proxy local respondendo"
            return 0
        fi
        sleep 2
    done
    warn "Proxy local nao respondeu em 60s"
    return 1
}

extract_tunnel_url() {
    docker logs enel-cloudflared 2>&1 \
        | grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' \
        | tail -1 \
        || true
}

wait_tunnel_url() {
    step "Aguardando Cloudflare Tunnel publicar URL..."
    local url=""
    for i in $(seq 1 40); do
        url="$(extract_tunnel_url)"
        [[ -n "${url}" ]] && { echo "${url}"; return 0; }
        sleep 2
    done
    return 1
}

cmd_up() {
    step "Iniciando stack de compartilhamento..."
    "${DC[@]}" up -d --build

    wait_streamlit_healthy || true
    wait_local_ready || true

    local url
    url="$(wait_tunnel_url || true)"

    echo
    echo "═══════════════════════════════════════════════════════════════════"
    if [[ -n "${url}" ]]; then
        ok "Dashboard publico: ${url}"
    else
        warn "Tunel ainda nao pronto. Tente: $0 url"
    fi
    ok "Acesso local:    http://localhost:8080"
    echo "  · Status:    $0 status"
    echo "  · Logs:      $0 logs"
    echo "  · Derrubar:  $0 down"
    echo "═══════════════════════════════════════════════════════════════════"
}

cmd_url() {
    local url
    url="$(extract_tunnel_url)"
    if [[ -z "${url}" ]]; then
        err "Tunel nao encontrado. Rode: $0 up"
        exit 1
    fi
    echo "${url}"
}

cmd_logs() {
    "${DC[@]}" logs -f --tail=80
}

cmd_status() {
    step "Containers:"
    docker ps --filter name=enel-streamlit --filter name=enel-caddy --filter name=enel-cloudflared \
        --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

    echo
    step "Health do Streamlit:"
    docker inspect -f '  {{.State.Health.Status}}' enel-streamlit 2>/dev/null || echo "  (container ausente)"

    echo
    step "Endpoint local:"
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/ || echo erro)"
    echo "  http://localhost:8080/   → HTTP ${code}"

    echo
    step "Endpoint publico:"
    local url
    url="$(extract_tunnel_url)"
    if [[ -n "${url}" ]]; then
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${url}/" || echo erro)"
        echo "  ${url}/   → HTTP ${code}"
    else
        echo "  (tunel sem URL ainda)"
    fi
}

cmd_rebuild() {
    step "Reconstruindo imagem Streamlit sem cache..."
    "${DC[@]}" build --no-cache streamlit
    "${DC[@]}" up -d --force-recreate streamlit
    wait_streamlit_healthy || true
    ok "Rebuild concluido."
}

cmd_down() {
    step "Parando stack..."
    "${DC[@]}" down
}

case "${1:-up}" in
    up)      cmd_up ;;
    url)     cmd_url ;;
    logs)    cmd_logs ;;
    status)  cmd_status ;;
    rebuild) cmd_rebuild ;;
    down)    cmd_down ;;
    *)       echo "Uso: $0 {up|url|logs|status|rebuild|down}"; exit 1 ;;
esac
