# 🚨 Crypto News Alert System

Real-time cryptocurrency news and security alert system for influencers and crypto professionals. Get push notifications for breaking crypto news, security breaches, regulatory updates, and protocol changes.

## Features

- 📡 **Multi-source aggregation**: RSS feeds, Nitter (Twitter/X), and Nostr
- 🔔 **Instant push notifications**: Via ntfy (mobile + desktop)
- 🎯 **Priority scoring**: Bilingual keyword matching (EN + PT-BR)
- 🔐 **Security-focused**: Critical alerts for hacks, exploits, breaches
- 📜 **Regulatory tracking**: Global and Brazil-specific (CVM, BCB)
- 🔄 **Deduplication**: Redis-backed to prevent spam
- 🐳 **Docker-ready**: One-command deployment

## Quick Start

### 1. Clone and Configure

```bash
cd ~/Projects/git/Crypto-News-Alerts

# Copy and edit configuration
cp .env.example .env
nano .env
```

### 2. Start with Docker Compose

```bash
docker compose up -d
```

### 3. Subscribe to Notifications

Install the **ntfy app** on your devices:
- 📱 Android: [Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
- 🍎 iOS: [App Store](https://apps.apple.com/app/ntfy/id1625396347)
- 🖥️ Desktop: Open `http://localhost:8080` in your browser

Subscribe to your notification topics:
- `crypto-critical` - Security breaches, hacks (🔴 urgent)
- `crypto-regulatory` - Regulatory news (🟠 high)
- `crypto-protocol` - Protocol updates (🟡 normal)
- `crypto-social` - Influencer posts (🟢 low)

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NTFY_URL` | `http://localhost:8080` | ntfy server URL |
| `NTFY_TOKEN` | - | Optional auth token |
| `REDIS_URL` | `redis://localhost:6379` | Redis for deduplication |
| `LOG_LEVEL` | `INFO` | Logging level |
| `TZ` | `America/Sao_Paulo` | Timezone |

### Sources Configuration

Edit `config/sources.yaml` to add/remove:
- RSS feeds
- Nitter/Twitter accounts
- Nostr public keys

### Filter Configuration

Edit `config/filters.yaml` to customize:
- Keyword lists (EN + PT-BR)
- Priority scoring weights
- Minimum score threshold

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Sources                             │
├─────────────┬─────────────┬──────────────┬─────────────────-┤
│ RSS Feeds   │ Nitter/X    │ Nostr Relays │ GitHub Releases  │
└──────┬──────┴──────┬──────┴───────┬──────┴─────────┬────────┘
       │             │              │                │
       └─────────────┴──────────────┴────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Alert Collector   │
                    │    (Python)        │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
       ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
       │ Priority    │ │ Deduplicator│ │ ntfy Client │
       │ Scorer      │ │   (Redis)   │ │             │
       └─────────────┘ └─────────────┘ └──────┬──────┘
                                              │
                              ┌───────────────┼───────────────┐
                              │               │               │
                       ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
                       │   Mobile    │ │   Desktop   │ │   Browser   │
                       │    Push     │ │    Push     │ │    Push     │
                       └─────────────┘ └─────────────┘ └─────────────┘
```

## Monitored Sources

### Security Experts
- @zachxbt - On-chain investigations
- @samczsun - DeFi security
- @Spreekaway - Real-time incidents
- @lopp - Bitcoin security
- @PeckShieldAlert - Security audits
- @CertiKAlert - Smart contract audits

### News Sources
- Rekt News - Hack reports
- CoinDesk - Global news
- Bitcoin Magazine - Protocol updates
- Portal do Bitcoin - Brazil 🇧🇷
- Livecoins - Brazil 🇧🇷

## Development

### Running Locally (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run collector
python -m src.main
```

### Testing Notifications

```bash
# Send a test notification
curl -d "🧪 Test alert from Crypto News Alerts" \
  http://localhost:8080/crypto-critical
```

## Customization

### Adding New RSS Feeds

Add to `config/sources.yaml`:

```yaml
rss_feeds:
  - name: "My Feed"
    url: "https://example.com/feed.xml"
    check_interval: 120
    priority_boost: 10
    category: "news"
```

### Adding New Keywords

Add to `config/filters.yaml`:

```yaml
keywords:
  critical_en:
    score: 50
    words:
      - "my-keyword"
```

## License

MIT License - Use freely for your crypto monitoring needs.

## Contributing

PRs welcome! Please focus on:
- Adding new data sources
- Improving keyword filters
- Better deduplication logic
