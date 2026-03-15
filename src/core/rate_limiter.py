"""Rate limiter with exponential backoff and User-Agent rotation."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


def random_user_agent() -> str:
    """Return a random User-Agent string."""
    return random.choice(USER_AGENTS)


@dataclass
class RateLimiter:
    """Per-domain rate limiter with exponential backoff.

    Usage::

        limiter = RateLimiter(base_delay=1.0)
        await limiter.wait("google.com")    # sleeps if needed
        limiter.report_success("google.com")
        # or
        limiter.report_failure("google.com")  # increases delay for next call
    """

    base_delay: float = 1.5
    max_delay: float = 120.0
    jitter: float = 0.5
    backoff_factor: float = 2.0

    _domain_state: dict[str, _DomainState] = field(default_factory=dict)

    def _get(self, domain: str) -> _DomainState:
        if domain not in self._domain_state:
            self._domain_state[domain] = _DomainState(
                current_delay=self.base_delay,
                consecutive_failures=0,
                last_request_time=0.0,
            )
        return self._domain_state[domain]

    async def wait(self, domain: str) -> None:
        """Wait the appropriate delay before making a request to *domain*."""
        state = self._get(domain)
        now = time.monotonic()
        elapsed = now - state.last_request_time
        jitter_val = random.uniform(0, self.jitter)
        wait_time = max(0.0, state.current_delay + jitter_val - elapsed)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        state.last_request_time = time.monotonic()

    def report_success(self, domain: str) -> None:
        """Reset backoff after a successful request."""
        state = self._get(domain)
        state.consecutive_failures = 0
        state.current_delay = self.base_delay

    def report_failure(self, domain: str) -> None:
        """Increase delay after a failed / rate-limited request."""
        state = self._get(domain)
        state.consecutive_failures += 1
        state.current_delay = min(
            self.max_delay,
            state.current_delay * self.backoff_factor,
        )

    def get_delay(self, domain: str) -> float:
        """Return the current delay for a domain (for logging)."""
        return self._get(domain).current_delay


@dataclass
class _DomainState:
    current_delay: float
    consecutive_failures: int
    last_request_time: float
