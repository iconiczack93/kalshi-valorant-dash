# kalshi-valorant-dash

Live VCT Valorant odds tracker powered by Kalshi's public prediction-market API and GitHub Pages.

**Live dashboard:** [iconiczack93.github.io/kalshi-valorant-dash](https://iconiczack93.github.io/kalshi-valorant-dash/)

## What it does

- **VCT-only market polling (`poller.py`):** Pulls open markets across `KXVALORANTGAME`, `KXVALORANTMAP`, and `KXVALORANTTOTALMAPS` and filters to Tier-1 VCT rosters (Americas, EMEA, Pacific, CN).
- **Rolling price history:** Tracks bid/ask midpoints and volume into `data.json` and maintains rolling sparkline history (up to 288 snapshots per contract) in `history.json`.
- **Zero-backend hosting:** A scheduled GitHub Actions workflow runs `poller.py` and commits updated JSON snapshots directly to the static GitHub Pages frontend (`index.html`).
- **Optional encrypted portfolio view:** When `KALSHI_KEY_ID`, `KALSHI_PRIVATE_KEY`, and `POSITIONS_PIN` secrets are configured, `poller.py` signs authenticated balance/position requests (RSA-PSS) and encrypts the portfolio payload client-side with PBKDF2-SHA256 (200k iterations) + AES-256-GCM before writing to `data.json`. Without `POSITIONS_PIN`, portfolio data is never published.

## Run locally

```bash
python3 poller.py
python3 -m http.server 8000
```

Then open `http://localhost:8000`.
