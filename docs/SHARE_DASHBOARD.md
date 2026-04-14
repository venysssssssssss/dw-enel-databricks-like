# Compartilhando o Dashboard de Erros de Leitura

Este guia mostra como expor o dashboard Streamlit local em uma URL publica HTTPS
para compartilhamento com a coordenacao, **sem** precisar configurar port-forward
no roteador, IP fixo ou certificado SSL manualmente.

## Arquitetura

```
[Browser da coordenacao]
        │  HTTPS
        ▼
[Cloudflare Edge]  ←───────  trycloudflare.com (URL publica gerada)
        │
        │  tunel persistente (saida do seu notebook)
        ▼
[cloudflared (container)]
        │  HTTP
        ▼
[Caddy reverse proxy] :8080
        │  HTTP + WebSocket
        ▼
[Streamlit] :8501
        │
        ▼
   dashboard erro_leitura_dashboard.py
```

### Por que essa pilha

| Componente | Papel | Por que |
|---|---|---|
| **Streamlit** | Servidor do dashboard | Ja e o runtime do app |
| **Caddy** | Proxy reverso local | Adiciona headers de seguranca, gzip, suporte a WebSocket, autenticacao basica opcional |
| **Cloudflared (quick tunnel)** | Tunel HTTPS publico | Nao exige IP fixo, nao exige conta paga, NAT-friendly, HTTPS valido |

O IP publico do notebook (`181.216.222.98`) nao e exposto — o trafego sai de dentro
via tunel. Isso e mais seguro do que abrir porta no roteador.

## Pre-requisitos

- Docker + Docker Compose plugin (`docker compose version`)
- Projeto clonado em `/home/vanys/BIG/dw-enel-databricks-like`

## Uso

```bash
# 1. Subir stack + gerar URL publica
./scripts/share_dashboard.sh up

# 2. Reimprimir a URL do tunel (util se a sessao terminou)
./scripts/share_dashboard.sh url

# 3. Stream de logs
./scripts/share_dashboard.sh logs

# 4. Parar tudo
./scripts/share_dashboard.sh down
```

A saida de `up` imprime algo como:

```
═══════════════════════════════════════════════════════════════════
  ✓ Dashboard publico disponivel em:
    https://random-words-1234.trycloudflare.com
  · Local:   http://localhost:8080
═══════════════════════════════════════════════════════════════════
```

Essa URL e descartavel — muda a cada `up`. Para URL fixa, veja "URL permanente".

## Seguranca recomendada

O modo padrao expoe **sem autenticacao**. Para uso com a coordenacao, habilite
Basic Auth no Caddy:

1. Gere um hash de senha:
   ```bash
   docker run --rm caddy caddy hash-password --plaintext 'SenhaForte123'
   ```
2. Edite `infra/config/caddy/Caddyfile`, descomente o bloco `basicauth` e cole o hash:
   ```
   basicauth {
       enel <hash-gerado>
   }
   ```
3. Reinicie: `./scripts/share_dashboard.sh down && ./scripts/share_dashboard.sh up`

Agora o navegador pedira usuario (`enel`) + senha.

## URL permanente (Cloudflare Tunnel autenticado)

O modo acima usa **quick tunnels** — otimo para demo rapida, mas a URL muda.
Para URL fixa (ex.: `erros-leitura.seudominio.com`):

1. Crie uma conta Cloudflare gratuita e adicione um dominio.
2. Instale `cloudflared` localmente, rode `cloudflared tunnel login` e crie um tunel nomeado:
   ```bash
   cloudflared tunnel create enel-erros-leitura
   cloudflared tunnel route dns enel-erros-leitura erros-leitura.seudominio.com
   ```
3. Substitua o servico `cloudflared` no `docker-compose.share.yml` por um com credenciais
   montadas e `command: tunnel run enel-erros-leitura`.

Documentacao: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/

## Alternativas (se Cloudflare nao estiver disponivel)

### a) ngrok
```bash
# Em vez do cloudflared, rode um unico container:
docker run --rm -p 4040:4040 -e NGROK_AUTHTOKEN="<token>" \
  ngrok/ngrok:latest http host.docker.internal:8080
```
URL publica em `http://localhost:4040`.

### b) Port-forward no roteador (menos seguro)
- Abrir TCP 8080 no roteador → LAN IP do notebook
- URL: `http://181.216.222.98:8080` (HTTP apenas, sem criptografia — **nao recomendado**)
- Requer IP fixo contratado com o provedor (seu IP pode mudar)

### c) Tailscale Funnel (necessita conta Tailscale)
- `tailscale funnel 8080` expoe com URL HTTPS persistente.

## Troubleshooting

| Sintoma | Causa provavel | Solucao |
|---|---|---|
| Streamlit nao carrega dados | `data/silver/...csv` ausente | `make pipeline` ou ajuste caminho na sidebar |
| Tunel pronto mas 502 no browser | Streamlit ainda instalando deps | Aguarde 30-60s na primeira subida |
| Nenhuma URL aparece | `cloudflared` sem internet | `docker logs enel-cloudflared` |
| WebSocket desconecta | Proxy sem upgrade correto | Caddy ja trata — verifique Caddyfile intacto |
| Porta 8080 ocupada | Outro servico local | Ajuste mapeamento no `docker-compose.share.yml` |

## Ciclo tipico para apresentar para a coordenacao

```bash
# 1. Garantir dados e artefatos prontos
make pipeline               # bronze → silver → gold
make erro-leitura-train     # topicos + classificador

# 2. Subir compartilhamento
./scripts/share_dashboard.sh up

# 3. Copiar URL e enviar no chat da coordenacao
./scripts/share_dashboard.sh url

# 4. Ao fim da apresentacao
./scripts/share_dashboard.sh down
```
