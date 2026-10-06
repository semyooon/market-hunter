# Market Hunter

Private, read-only marketplace search and watch service. It is designed for personal deal hunting: one normalized API for approved sources, a local SQLite history, and an MCP bridge that Codex can call.

The first profile is deliberately opinionated for the NAS hunt:

- Bulgarian/EU search, with delivery to Bulgaria in mind;
- enterprise/refurb drives welcome, but CMR only;
- 12–20 TB preferred; Exos, Ultrastar and Toshiba MG get a score uplift;
- SAS is flagged for its HBA/cabling cost; SMR is rejected;
- the target is at most €24/TB delivered, with a maximum attractive price in each card.

## What is included in v0.1

- `POST /v1/search` — query eBay Browse API and OLX.bg, normalize and rank results;
- SQLite storage and stable listing IDs for comparisons/history;
- saved watches and a polling worker (logs new matches; notification delivery is intentionally deferred);
- a local stdio MCP server exposing `search_listings`, `get_listing`, `create_watch`, and `list_watches`;
- no credentials, purchases, messages, or arbitrary URL-fetching tools.

## Run locally

```bash
cd market-hunter
cp .env.example .env
uv sync --all-groups
uv run pytest
uv run market-hunter-api
```

In another terminal:

```bash
curl -X POST http://127.0.0.1:8000/v1/search \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $(grep MARKET_HUNTER_API_TOKEN .env | cut -d= -f2)" \
  -d '{"query":"WD Ultrastar 20TB SATA", "profile":"nas_hdd", "sources":["olx_bg","ebay"]}'
```

During local development, leave `MARKET_HUNTER_API_TOKEN` empty if the endpoint is not reachable outside your machine. Set a high-entropy value before any remote access.

For eBay, create a free eBay Developer application and set its Browse API client ID and client secret in `.env`. This is intentionally an official API adapter: the interactive eBay results page is JavaScript-driven and brittle to scrape.

## Connect Codex desktop

Use a local stdio MCP bridge rather than exposing the VPS publicly. Add this to your user Codex `config.toml` (on Windows, usually `%USERPROFILE%\.codex\config.toml`):

```toml
[mcp_servers.market_hunter]
command = "uv"
args = ["run", "--directory", "C:\path\to\market-hunter", "market-hunter-mcp"]

[mcp_servers.market_hunter.env]
MARKET_HUNTER_API_URL = "http://127.0.0.1:8000"
MARKET_HUNTER_API_TOKEN = "the-same-long-token-as-the-api"
```

Restart Codex after saving. When the service moves to the VPS, replace `MARKET_HUNTER_API_URL` with its Tailscale or WireGuard address. The desktop MCP process stays local; only your laptop establishes the private network connection.

## VPS deployment

1. Install Docker Compose and Tailscale or WireGuard on the VPS.
2. Copy the repository, create `.env` from `.env.example`, and replace the API token.
3. Start the service with `docker compose up -d --build`.
4. Keep the compose port binding at `127.0.0.1:8000`; publish it only through the private VPN, not a public reverse proxy.
5. Point the local MCP bridge at the private VPN address and test `search_listings` in Codex.

If you later want ChatGPT web to call it directly, deploy a proper authenticated MCP endpoint or use OpenAI Secure MCP Tunnel; do not expose this API with only an obscured URL.

## Security model

- The API accepts only fixed providers and validated fields. There is no `fetch_url` endpoint, avoiding an SSRF primitive.
- Listing descriptions are data, not instructions. The MCP server tells the model to treat them as untrusted.
- The MCP tools are read-only except explicit watch creation. They never message sellers, authenticate to marketplaces, or buy anything.
- Keep source request rates low, cache results, and respect each source's terms and access controls. If a source blocks automated requests, disable its adapter rather than trying to bypass that protection.

## Known limits

- Marketplace HTML changes. Each adapter is isolated and has fixture tests, but it may need maintenance.
- OLX cards do not reliably reveal delivery cost; its score uses the asking price until shipping is verified.
- Currency conversion is fixed for rough ranking, not a live FX quote.
