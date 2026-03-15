"""Username existence checker across popular platforms.

Instead of shelling out to Sherlock, this module checks a curated list of
platforms directly via HTTP HEAD/GET probes.  This gives us full control
over rate limiting, stealth, and result parsing.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from src.models.result import ConfidenceLevel, ResultStatus, ScanResult
from src.models.user_profile import UserProfile
from src.modules.base import BaseModule

# Platform definitions: each entry maps a platform name to its profile URL
# template and the HTTP status that indicates "user exists".
@dataclass(frozen=True)
class PlatformDef:
    name: str
    url_template: str  # must contain {username}
    exists_status: int = 200
    missing_indicators: tuple[str, ...] = ()  # strings in body that mean "not found"


PLATFORMS: list[PlatformDef] = [
    PlatformDef("GitHub", "https://github.com/{username}"),
    PlatformDef("GitLab", "https://gitlab.com/{username}"),
    PlatformDef("Reddit", "https://www.reddit.com/user/{username}/about.json"),
    PlatformDef("Medium", "https://medium.com/@{username}"),
    PlatformDef("Dev.to", "https://dev.to/{username}"),
    PlatformDef("Keybase", "https://keybase.io/{username}"),
    PlatformDef("HackerNews", "https://hacker-news.firebaseio.com/v0/user/{username}.json"),
    PlatformDef("Replit", "https://replit.com/@{username}"),
    PlatformDef("PyPI", "https://pypi.org/user/{username}/"),
    PlatformDef("npm", "https://www.npmjs.com/~{username}"),
    PlatformDef("Gravatar", "https://en.gravatar.com/{username}.json"),
    PlatformDef("Pastebin", "https://pastebin.com/u/{username}"),
    PlatformDef(
        "Steam",
        "https://steamcommunity.com/id/{username}",
        missing_indicators=("The specified profile could not be found.",),
    ),
    PlatformDef("Pinterest", "https://www.pinterest.com/{username}/"),
    PlatformDef("Telegram", "https://t.me/{username}"),
    PlatformDef("TikTok", "https://www.tiktok.com/@{username}"),
    PlatformDef("Twitch", "https://www.twitch.tv/{username}"),
    PlatformDef("SoundCloud", "https://soundcloud.com/{username}"),
    PlatformDef("Spotify", "https://open.spotify.com/user/{username}"),
    PlatformDef("Flickr", "https://www.flickr.com/people/{username}/"),
]

MAX_CONCURRENT = 5  # limit concurrent checks per username


class UsernameChecker(BaseModule):
    """Check username existence across platforms."""

    name = "username_checker"

    async def run(self, profile: UserProfile) -> list[ScanResult]:
        candidates = list(dict.fromkeys(
            profile.usernames + profile.nicknames
        ))
        if not candidates:
            return []

        results: list[ScanResult] = []
        for username in candidates:
            batch = await self._check_username(username)
            results.extend(batch)
        return results

    async def _check_username(self, username: str) -> list[ScanResult]:
        """Probe all platforms for a single username, with concurrency limit."""
        sem = asyncio.Semaphore(MAX_CONCURRENT)
        results: list[ScanResult] = []

        async def probe(platform: PlatformDef) -> None:
            async with sem:
                result = await self._probe_platform(username, platform)
                if result:
                    await self._save(result)
                    results.append(result)

        tasks = [probe(p) for p in PLATFORMS]
        await asyncio.gather(*tasks, return_exceptions=True)
        return results

    async def _probe_platform(self, username: str, platform: PlatformDef) -> ScanResult | None:
        """Check a single platform for a username."""
        url = platform.url_template.format(username=username)
        resp = await self.client.get(url)

        status_code = resp.get("status", 0)
        body = resp.get("body", "")
        error = resp.get("error")

        if error:
            return ScanResult(
                module=self.name,
                query=username,
                platform=platform.name,
                url=url,
                status=ResultStatus.ERROR,
                confidence=ConfidenceLevel.UNVERIFIED,
                raw_data={"error": error},
                matched_fields=["usernames"],
            )

        # Check for explicit "not found" indicators in body
        if platform.missing_indicators:
            for indicator in platform.missing_indicators:
                if indicator in body:
                    return None  # skip not-found silently

        if status_code == platform.exists_status:
            return ScanResult(
                module=self.name,
                query=username,
                platform=platform.name,
                url=url,
                title=f"{username} on {platform.name}",
                status=ResultStatus.FOUND,
                confidence=ConfidenceLevel.MEDIUM,
                matched_fields=["usernames"],
            )

        return None  # not found, no need to record
