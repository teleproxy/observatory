# Telegram Censorship Observatory

Live monitoring of Telegram accessibility from multiple regions.

Probes run hourly from different locations and perform two tests:

- **Direct connectivity** — TCP connect to all 5 Telegram production DCs on port 443
- **Proxy E2E** — Full Telegram API call through a [Teleproxy](https://github.com/teleproxy/teleproxy) instance using fake-TLS transport

Results are published at [teleproxy.github.io/observatory](https://teleproxy.github.io/observatory/).

## Running probes locally

```bash
pip install -r requirements.txt

# Direct-only (no proxy env vars needed):
python -m probes.runner --probe-id local --region "Local"

# With proxy E2E:
PROXY_HOST=... PROXY_PORT=... PROXY_SECRET=... PROXY_DOMAIN=... \
TG_BOT_TOKEN=... \
python -m probes.runner --probe-id local --region "Local"
```

## Adding a probe location

Set up a self-hosted GitHub Actions runner with appropriate labels, then add a job to `.github/workflows/probe.yml`.
