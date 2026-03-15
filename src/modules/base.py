"""Base class for all OSINT scanner modules."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.http_client import StealthClient
from src.core.jsonl_logger import JsonlLogger
from src.core.state_manager import StateManager
from src.models.result import ScanResult
from src.models.user_profile import UserProfile


class BaseModule(ABC):
    """Abstract base for OSINT modules.

    Every module receives the shared StealthClient, StateManager, and
    JsonlLogger so results are persisted in real-time.
    """

    name: str = "base"

    def __init__(
        self,
        client: StealthClient,
        state_manager: StateManager,
        jsonl_logger: JsonlLogger,
        scan_id: str,
    ) -> None:
        self.client = client
        self.state = state_manager
        self.jsonl = jsonl_logger
        self.scan_id = scan_id

    @abstractmethod
    async def run(self, profile: UserProfile) -> list[ScanResult]:
        """Execute the module's scan logic against the given profile.

        Implementations must persist each result via self._save() as they go.
        """
        ...

    async def _save(self, result: ScanResult) -> None:
        """Persist a single result to both SQLite and JSONL."""
        await self.state.save_result(self.scan_id, result)
        self.jsonl.log_result(result)
