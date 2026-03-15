"""Stealth-aware async HTTP client wrapping aiohttp."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import aiohttp

from src.core.rate_limiter import RateLimiter, random_user_agent


class StealthClient:
    """Async HTTP client with automatic rate limiting and UA rotation.

    Usage::

        async with StealthClient() as client:
            resp = await client.get("https://example.com/search?q=test")
            print(resp["status"], resp["body"])
    """

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.rate_limiter = rate_limiter or RateLimiter()
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> StealthClient:
        self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc

    async def get(self, url: str, params: dict | None = None) -> dict:
        """Perform a rate-limited GET request with a random User-Agent."""
        assert self._session is not None, "Use 'async with StealthClient()' context manager"
        domain = self._domain(url)
        await self.rate_limiter.wait(domain)

        headers = {
            "User-Agent": random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with self._session.get(url, headers=headers, params=params, ssl=False) as resp:
                body = await resp.text()
                status = resp.status

                if status == 429 or status >= 500:
                    self.rate_limiter.report_failure(domain)
                else:
                    self.rate_limiter.report_success(domain)

                return {"status": status, "body": body, "url": str(resp.url)}
        except (aiohttp.ClientError, TimeoutError) as exc:
            self.rate_limiter.report_failure(domain)
            return {"status": 0, "body": "", "url": url, "error": str(exc)}

    async def get_json(self, url: str, params: dict | None = None) -> dict:
        """Perform a rate-limited GET and parse JSON response."""
        assert self._session is not None
        domain = self._domain(url)
        await self.rate_limiter.wait(domain)

        headers = {
            "User-Agent": random_user_agent(),
            "Accept": "application/json",
        }

        try:
            async with self._session.get(url, headers=headers, params=params, ssl=False) as resp:
                status = resp.status

                if status == 429 or status >= 500:
                    self.rate_limiter.report_failure(domain)
                    return {"status": status, "data": None, "error": f"HTTP {status}"}
                else:
                    self.rate_limiter.report_success(domain)

                data = await resp.json(content_type=None)
                return {"status": status, "data": data, "url": str(resp.url)}
        except (aiohttp.ClientError, TimeoutError) as exc:
            self.rate_limiter.report_failure(domain)
            return {"status": 0, "data": None, "error": str(exc)}
