# TraceCleaner

A modular OSINT (Open Source Intelligence) tool that maps a user's digital footprint across the internet by cross-correlating multi-dimensional personal data.

## Features

- **Dynamic User Profiling** — Accepts unlimited variations of personal data (names, emails, usernames, addresses, schools, workplaces, etc.) via Pydantic v2 models
- **Cross-Correlation Engine** — Generates intelligent search permutations by combining profile fields (e.g. `first_name + school`, `nickname + city`, `email_prefix + last_name`)
- **Google Dorking** — Automated dork query generation with `site:`, `inurl:`, and exact-match operators via DuckDuckGo
- **Username Checker** — Probes 20+ platforms (GitHub, Reddit, Medium, TikTok, Steam, etc.) for username existence
- **HIBP Integration** — Checks emails against Have I Been Pwned breach database and PwnedPasswords k-anonymity API
- **Stealth & Rate Limiting** — Per-domain exponential backoff with jitter and User-Agent rotation to avoid IP bans
- **Crash-Safe Persistence** — Dual storage: SQLite for structured queries + JSONL for append-only streaming backup
- **Resume Capability** — Interrupted scans can be resumed from where they left off
- **Report Export** — Auto-generates JSON and CSV reports after each scan
- **Rich CLI** — Interactive terminal UI with colored output and result tables

## Project Structure

```
TraceCleaner/
├── src/
│   ├── core/
│   │   ├── correlator.py      # Cross-correlation permutation engine
│   │   ├── exporter.py        # JSON/CSV report generator
│   │   ├── http_client.py     # Stealth async HTTP client
│   │   ├── jsonl_logger.py    # Append-only JSONL backup logger
│   │   ├── rate_limiter.py    # Per-domain exponential backoff
│   │   ├── scanner.py         # Scan orchestrator
│   │   └── state_manager.py   # SQLite persistence layer
│   ├── models/
│   │   ├── user_profile.py    # UserProfile schema (20+ fields)
│   │   └── result.py          # ScanResult & ScanState schemas
│   ├── modules/
│   │   ├── base.py            # Abstract base for OSINT modules
│   │   ├── username_checker.py # Multi-platform username probe
│   │   ├── dorking.py         # DuckDuckGo search with dork operators
│   │   └── hibp_checker.py    # Have I Been Pwned integration
│   ├── utils/
│   │   └── logger.py          # Rich-powered logging
│   └── cli.py                 # Interactive CLI interface
├── tests/                     # 23 unit tests
├── data/                      # SQLite DB, JSONL logs, reports
├── main.py                    # Entry point
├── memory.md                  # Session continuity file
└── requirements.txt
```

## Installation

```bash
git clone https://github.com/sedat4ras/DeleteMe.git
cd DeleteMe

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## Usage

### Interactive Mode

```bash
python main.py
```

The CLI will prompt you to enter data for each field (names, emails, usernames, etc.). Separate multiple values with commas.

### From JSON Profile

```bash
python main.py --profile data/sample_profile.json
```

Example profile JSON:

```json
{
    "first_names": ["John"],
    "last_names": ["Doe"],
    "nicknames": ["johndoe99", "jdoe"],
    "emails": ["johndoe99@example.com"],
    "usernames": ["johndoe99"],
    "birth_cities": ["Springfield"],
    "schools": ["Springfield High"],
    "keywords": ["photography", "linux"]
}
```

### Resume an Interrupted Scan

```bash
python main.py --resume <scan_id>
```

If a scan is interrupted (Ctrl+C), progress is automatically saved. On the next run, you'll be prompted to resume.

## Configuration

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `HIBP_API_KEY` | Optional | Have I Been Pwned API key for full breach lookups |

## Running Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

## Supported Platforms (Username Checker)

GitHub, GitLab, Reddit, Medium, Dev.to, Keybase, HackerNews, Replit, PyPI, npm, Gravatar, Pastebin, Steam, Pinterest, Telegram, TikTok, Twitch, SoundCloud, Spotify, Flickr

## Tech Stack

- **Python 3.11+** with `asyncio`
- **aiohttp** — Async HTTP requests
- **aiosqlite** — Async SQLite persistence
- **Pydantic v2** — Data validation and modeling
- **Rich** — Terminal UI and formatting
- **tenacity** — Retry logic

## Disclaimer

This tool is intended for **authorized security research**, **penetration testing**, and **personal digital footprint awareness** only. Always ensure you have proper authorization before scanning any individual. The authors are not responsible for any misuse of this tool.

## License

MIT
