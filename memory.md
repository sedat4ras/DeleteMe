# TraceCleaner - Memory File

## Project Roadmap

1. **Infrastructure & Data Layer** - Directory structure, requirements, Pydantic models
2. **State Management** - SQLite persistence layer, JSONL logging, resume capability
3. **Cross-Correlation Engine** - Permutation generator for multi-dimensional data
4. **Rate Limiting & Stealth** - Exponential backoff, User-Agent rotation
5. **OSINT Modules** - Username checker, Google Dorking (DuckDuckGo), HIBP
6. **CLI Interface** - Rich-based terminal UI, interactive profile builder
7. **Scan Orchestrator** - Module runner with resume and error handling
8. **Report Exporter** - JSON and CSV output
9. **Testing** - 23 unit tests, all passing
10. **Future: Additional modules** - Social media scrapers, Wayback Machine, DNS lookups

## Completed Modules

- [x] Directory structure (`src/core/`, `src/models/`, `src/modules/`, `src/utils/`, `data/`, `tests/`)
- [x] `requirements.txt` (pydantic, aiohttp, aiosqlite, rich, tenacity, pytest, pytest-asyncio)
- [x] `UserProfile` Pydantic model — 20 fields + custom_fields (`src/models/user_profile.py`)
- [x] `ScanResult` + `ScanState` models (`src/models/result.py`)
- [x] `StateManager` — async SQLite CRUD for sessions and results (`src/core/state_manager.py`)
- [x] `JsonlLogger` — append-only JSONL backup (`src/core/jsonl_logger.py`)
- [x] `Correlator` — permutation generator + dork query builder (`src/core/correlator.py`)
- [x] `RateLimiter` — per-domain exponential backoff with jitter (`src/core/rate_limiter.py`)
- [x] `StealthClient` — async HTTP with UA rotation (`src/core/http_client.py`)
- [x] `UsernameChecker` — probes 20 platforms (`src/modules/username_checker.py`)
- [x] `DorkingModule` — DuckDuckGo HTML search (`src/modules/dorking.py`)
- [x] `HibpChecker` — HIBP breach + PwnedPasswords (`src/modules/hibp_checker.py`)
- [x] `BaseModule` ABC (`src/modules/base.py`)
- [x] `Scanner` orchestrator (`src/core/scanner.py`)
- [x] `Exporter` — JSON/CSV reports (`src/core/exporter.py`)
- [x] Rich CLI with interactive profile builder (`src/cli.py`)
- [x] `main.py` with argparse (--profile, --resume)
- [x] Logger utility (`src/utils/logger.py`)
- [x] 23 unit tests (profile, correlator, state_manager, rate_limiter)
- [x] Sample profile JSON (`data/sample_profile.json`)
- [x] `.env.example` for HIBP API key

## Active Task (Where did I leave off?)

**All core tasks complete.** The project is fully functional end-to-end.

### Possible future enhancements:
- Add more OSINT modules (Wayback Machine, DNS/WHOIS, social media APIs)
- Add proxy rotation support to StealthClient
- Add integration tests with mocked HTTP responses
- Add export to HTML report with Rich formatting
- Add async concurrency across modules (run modules in parallel)
- Add progress bar with Rich Progress during scans

## Encountered Errors and Solutions

- **Pydantic deprecation warning:** Accessing `self.model_fields` on instance is deprecated in v2.11. Fixed by using `type(self).model_fields` instead.

## Key Architecture Decisions

- **DuckDuckGo over Google:** DorkingModule uses DuckDuckGo HTML to avoid Google's aggressive anti-bot. Simpler, fewer CAPTCHAs.
- **Built-in username checker vs Sherlock:** Custom implementation gives full control over rate limiting and result parsing instead of shelling out.
- **SQLite + JSONL dual persistence:** SQLite for structured queries/resume, JSONL for crash-safe streaming backup.
- **Per-domain rate limiting:** Each domain has independent backoff state, preventing one slow domain from blocking others.

## Git History

- `a6128fe` feat(infrastructure): project structure + Pydantic models
- `be91020` feat(core): SQLite state manager + JSONL logger
- `5e1cb02` feat(core): cross-correlation engine
- `92d0eb1` feat(core): rate limiter + stealth HTTP client
- `05db498` feat(modules): username checker, dorking, HIBP
- `7b21d42` feat(cli): Rich CLI + scanner orchestrator + main
- `db3866c` feat(tests): 23 tests, all passing
- `e36fc7e` feat(core): JSON/CSV report exporter
