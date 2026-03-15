"""Google Dorking module — search engine scraping for OSINT queries.

Uses DuckDuckGo HTML as the backend to avoid Google's aggressive
anti-bot measures.  Falls back gracefully on rate limits.
"""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import quote_plus

from src.core.correlator import Correlator
from src.models.result import ConfidenceLevel, ResultStatus, ScanResult
from src.models.user_profile import UserProfile
from src.modules.base import BaseModule

DUCKDUCKGO_URL = "https://html.duckduckgo.com/html/"


class DorkingModule(BaseModule):
    """Run dork queries via DuckDuckGo HTML and parse results."""

    name = "dorking"

    def __init__(self, *args, max_queries: int = 50, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.max_queries = max_queries

    async def run(self, profile: UserProfile) -> list[ScanResult]:
        correlator = Correlator(profile)
        dork_queries = correlator.generate_dork_queries()

        # Also add plain cross-correlated queries
        plain_queries = correlator.generate()

        # Merge, deduplicate, and cap
        seen: set[str] = set()
        queries: list[str] = []
        for perm in plain_queries + dork_queries:
            q = perm.query
            if q not in seen:
                seen.add(q)
                queries.append(q)
            if len(queries) >= self.max_queries:
                break

        # Check which queries were already completed (resume support)
        session = await self.state.get_session(self.scan_id)
        completed = set(session.completed_queries) if session else set()

        results: list[ScanResult] = []
        for query in queries:
            cache_key = f"dork:{query}"
            if cache_key in completed:
                continue

            batch = await self._search(query)
            results.extend(batch)

            # Mark query as completed for resume
            if session:
                session.completed_queries.append(cache_key)
                await self.state.update_session(session)

        return results

    async def _search(self, query: str) -> list[ScanResult]:
        """Execute a single DuckDuckGo HTML search and parse results."""
        resp = await self.client.get(
            DUCKDUCKGO_URL,
            params={"q": query, "kl": "us-en"},
        )

        if resp.get("error") or resp.get("status", 0) != 200:
            return [
                ScanResult(
                    module=self.name,
                    query=query,
                    status=ResultStatus.ERROR,
                    confidence=ConfidenceLevel.UNVERIFIED,
                    raw_data={"error": resp.get("error", f"HTTP {resp.get('status')}")},
                )
            ]

        return self._parse_results(query, resp.get("body", ""))

    def _parse_results(self, query: str, html: str) -> list[ScanResult]:
        """Extract search result entries from DuckDuckGo HTML response."""
        results: list[ScanResult] = []

        # DuckDuckGo HTML wraps each result in <a class="result__a" ...>
        link_pattern = re.compile(
            r'<a\s+[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        snippet_pattern = re.compile(
            r'<a\s+class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL,
        )

        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (url, raw_title) in enumerate(links):
            title = self._strip_html(raw_title)
            snippet = self._strip_html(snippets[i]) if i < len(snippets) else ""

            result = ScanResult(
                module=self.name,
                query=query,
                url=url,
                title=title,
                snippet=snippet,
                status=ResultStatus.FOUND,
                confidence=ConfidenceLevel.LOW,
                matched_fields=["dorking"],
            )
            self.jsonl.log_result(result)
            results.append(result)

        return results

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove HTML tags and unescape entities."""
        clean = re.sub(r"<[^>]+>", "", text)
        return unescape(clean).strip()
