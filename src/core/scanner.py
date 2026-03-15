"""Scan orchestrator — wires modules together and drives the scan lifecycle."""

from __future__ import annotations

import asyncio

from src.core.http_client import StealthClient
from src.core.jsonl_logger import JsonlLogger
from src.core.rate_limiter import RateLimiter
from src.core.state_manager import StateManager
from src.models.result import ScanResult, ScanState
from src.models.user_profile import UserProfile
from src.modules.base import BaseModule
from src.modules.dorking import DorkingModule
from src.modules.hibp_checker import HibpChecker
from src.modules.username_checker import UsernameChecker
from src.utils.logger import log


class Scanner:
    """High-level orchestrator that runs all OSINT modules against a profile."""

    def __init__(self, profile: UserProfile, resume_scan_id: str | None = None) -> None:
        self.profile = profile
        self.resume_scan_id = resume_scan_id
        self.state_manager = StateManager()
        self.rate_limiter = RateLimiter()
        self.scan_state: ScanState | None = None
        self.results: list[ScanResult] = []

    async def run(self) -> list[ScanResult]:
        """Execute the full scan pipeline."""
        await self.state_manager.connect()

        try:
            # Resume or create a new session
            if self.resume_scan_id:
                self.scan_state = await self.state_manager.get_session(self.resume_scan_id)
                if self.scan_state:
                    log.info(f"[bold green]Resuming scan[/] {self.scan_state.scan_id}")
                else:
                    log.warning("Scan ID not found, starting fresh.")

            if not self.scan_state:
                self.scan_state = ScanState()
                await self.state_manager.create_session(self.scan_state)
                log.info(f"[bold green]New scan started[/] {self.scan_state.scan_id}")

            scan_id = self.scan_state.scan_id
            jsonl = JsonlLogger(scan_id)
            jsonl.log_event("scan_start", {"profile_fields": self.profile.populated_field_names()})

            async with StealthClient(rate_limiter=self.rate_limiter) as client:
                modules: list[BaseModule] = [
                    UsernameChecker(client, self.state_manager, jsonl, scan_id),
                    DorkingModule(client, self.state_manager, jsonl, scan_id),
                    HibpChecker(client, self.state_manager, jsonl, scan_id),
                ]

                for module in modules:
                    log.info(f"[cyan]Running module:[/] {module.name}")
                    try:
                        module_results = await module.run(self.profile)
                        self.results.extend(module_results)
                        found = sum(1 for r in module_results if r.status.value == "found")
                        log.info(
                            f"[green]{module.name}[/] finished — "
                            f"{found} found / {len(module_results)} total"
                        )
                    except Exception as exc:
                        log.error(f"[red]{module.name} failed:[/] {exc}")
                        self.scan_state.last_error = f"{module.name}: {exc}"
                        await self.state_manager.update_session(self.scan_state)

            # Finalize
            self.scan_state.total_results = len(self.results)
            self.scan_state.is_complete = True
            await self.state_manager.update_session(self.scan_state)
            jsonl.log_event("scan_complete", {"total_results": len(self.results)})
            log.info(f"[bold green]Scan complete.[/] Total results: {len(self.results)}")

            return self.results

        finally:
            await self.state_manager.close()
