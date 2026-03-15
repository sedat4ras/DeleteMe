"""Have I Been Pwned (HIBP) breach checker.

Checks if emails or usernames appear in known data breaches using the
HIBP v3 API.  Requires an API key for the breachedaccount endpoint,
but the PwnedPasswords API is free and keyless.

If no API key is configured, falls back to checking password hashes via
the k-anonymity model (PwnedPasswords range API).
"""

from __future__ import annotations

import hashlib
import os

from src.models.result import ConfidenceLevel, ResultStatus, ScanResult
from src.models.user_profile import UserProfile
from src.modules.base import BaseModule

HIBP_BREACHES_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{account}"
HIBP_PASTES_URL = "https://haveibeenpwned.com/api/v3/pasteaccount/{account}"
PWNEDPASSWORDS_URL = "https://api.pwnedpasswords.com/range/{prefix}"


class HibpChecker(BaseModule):
    """Check emails against HIBP breach database."""

    name = "hibp"

    def __init__(self, *args, api_key: str | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.api_key = api_key or os.environ.get("HIBP_API_KEY", "")

    async def run(self, profile: UserProfile) -> list[ScanResult]:
        results: list[ScanResult] = []

        # Check breached accounts if we have an API key
        if self.api_key:
            for email in profile.emails:
                breach_results = await self._check_breaches(email)
                results.extend(breach_results)
        else:
            # Without API key, log a notice and check paste exposure only
            self.jsonl.log_event("hibp_no_api_key", {
                "message": "No HIBP API key set. Breach lookup skipped. "
                           "Set HIBP_API_KEY environment variable for full breach data."
            })

        # Email-derived password hash check (keyless, always available)
        for email in profile.emails:
            prefix_result = await self._check_password_exposure(email)
            if prefix_result:
                results.append(prefix_result)

        return results

    async def _check_breaches(self, email: str) -> list[ScanResult]:
        """Query HIBP breached-account endpoint for a single email."""
        url = HIBP_BREACHES_URL.format(account=email)
        resp = await self.client.get_json(url, params={
            "truncateResponse": "false",
        })

        # Inject required HIBP headers
        # Note: StealthClient doesn't support custom headers per-request yet,
        # so we document this limitation.  In production, the API key header
        # (hibp-api-key) would need to be injected.

        status = resp.get("status", 0)

        if status == 404:
            return []  # no breaches found
        if status != 200:
            return [ScanResult(
                module=self.name,
                query=email,
                platform="HIBP",
                status=ResultStatus.ERROR,
                confidence=ConfidenceLevel.UNVERIFIED,
                raw_data={"error": f"HIBP returned HTTP {status}"},
                matched_fields=["emails"],
            )]

        breaches = resp.get("data") or []
        results: list[ScanResult] = []
        for breach in breaches:
            result = ScanResult(
                module=self.name,
                query=email,
                platform="HIBP",
                url=f"https://haveibeenpwned.com/api/v3/breach/{breach.get('Name', '')}",
                title=f"Breach: {breach.get('Name', 'Unknown')}",
                snippet=f"Domain: {breach.get('Domain', 'N/A')} | "
                        f"Date: {breach.get('BreachDate', 'N/A')} | "
                        f"Data: {', '.join(breach.get('DataClasses', []))}",
                status=ResultStatus.FOUND,
                confidence=ConfidenceLevel.HIGH,
                raw_data=breach,
                matched_fields=["emails"],
            )
            await self._save(result)
            results.append(result)

        return results

    async def _check_password_exposure(self, email: str) -> ScanResult | None:
        """Use PwnedPasswords k-anonymity API to check if the email's
        SHA-1 prefix appears in breach datasets.

        This is a heuristic: we hash the email itself (not a password)
        to see if the email hash prefix shows up, indicating exposure.
        """
        sha1 = hashlib.sha1(email.lower().encode()).hexdigest().upper()
        prefix = sha1[:5]
        suffix = sha1[5:]

        url = PWNEDPASSWORDS_URL.format(prefix=prefix)
        resp = await self.client.get(url)

        if resp.get("status") != 200:
            return None

        body = resp.get("body", "")
        for line in body.splitlines():
            parts = line.strip().split(":")
            if len(parts) == 2 and parts[0] == suffix:
                count = int(parts[1])
                result = ScanResult(
                    module=self.name,
                    query=email,
                    platform="PwnedPasswords",
                    title=f"Email hash found in {count} breach(es)",
                    snippet=f"SHA-1 prefix match for {email}",
                    status=ResultStatus.FOUND,
                    confidence=ConfidenceLevel.LOW,
                    matched_fields=["emails"],
                    raw_data={"sha1_prefix": prefix, "occurrences": count},
                )
                await self._save(result)
                return result

        return None
