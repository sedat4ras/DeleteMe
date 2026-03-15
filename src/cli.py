"""Interactive CLI for TraceCleaner using Rich."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from src.core.scanner import Scanner
from src.core.state_manager import StateManager
from src.models.user_profile import UserProfile

console = Console()

BANNER = r"""
 _____                    ____ _
|_   _| __ __ _  ___ ___ / ___| | ___  __ _ _ __   ___ _ __
  | || '__/ _` |/ __/ _ \ |   | |/ _ \/ _` | '_ \ / _ \ '__|
  | || | | (_| | (_|  __/ |___| |  __/ (_| | | | |  __/ |
  |_||_|  \__,_|\___\___|\____|_|\___|\__,_|_| |_|\___|_|
"""

# Fields to prompt the user for, in order
PROFILE_FIELDS: list[tuple[str, str]] = [
    ("first_names", "First name(s)"),
    ("last_names", "Last name(s) / maiden name(s)"),
    ("full_names", "Full name variations"),
    ("nicknames", "Nicknames / aliases / screen names"),
    ("emails", "Email addresses"),
    ("phone_numbers", "Phone numbers"),
    ("usernames", "Platform usernames / handles"),
    ("domains", "Personal / business domains"),
    ("social_urls", "Known social-media profile URLs"),
    ("birth_cities", "City/town of birth"),
    ("current_cities", "Current city/town"),
    ("past_addresses", "Past addresses / neighborhoods"),
    ("countries", "Countries of residence"),
    ("schools", "Schools / universities"),
    ("workplaces", "Companies / organizations"),
    ("job_titles", "Job titles / roles"),
    ("birth_dates", "Date(s) of birth"),
    ("pet_names", "Pet names"),
    ("hobbies", "Hobbies / interests"),
    ("keywords", "Free-form keywords"),
]


def collect_profile() -> UserProfile:
    """Interactively collect profile data from the user."""
    console.print(Panel(BANNER, style="bold cyan", expand=False))
    console.print(
        "[bold]Enter data for each field.[/] "
        "Separate multiple values with commas. Press Enter to skip.\n"
    )

    data: dict[str, list[str]] = {}
    for field_name, label in PROFILE_FIELDS:
        raw = Prompt.ask(f"  [cyan]{label}[/]", default="")
        values = [v.strip() for v in raw.split(",") if v.strip()]
        if values:
            data[field_name] = values

    # Custom fields
    if Confirm.ask("\n  Add custom fields?", default=False):
        while True:
            key = Prompt.ask("    Field name (empty to stop)", default="")
            if not key:
                break
            vals = Prompt.ask(f"    Values for '{key}' (comma-separated)", default="")
            parsed = [v.strip() for v in vals.split(",") if v.strip()]
            if parsed:
                data.setdefault("custom_fields", {})
                data["custom_fields"][key] = parsed

    profile = UserProfile(**data)
    populated = profile.populated_field_names()
    console.print(f"\n[green]Profile created with {len(populated)} populated field(s).[/]\n")
    return profile


def load_profile_from_json(path: str) -> UserProfile:
    """Load a UserProfile from a JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return UserProfile(**raw)


def display_results(results: list) -> None:
    """Print a summary table of scan results."""
    if not results:
        console.print("[yellow]No results found.[/]")
        return

    table = Table(title="Scan Results", show_lines=True)
    table.add_column("Module", style="cyan", width=18)
    table.add_column("Platform", style="magenta", width=16)
    table.add_column("Query", width=24)
    table.add_column("Status", width=10)
    table.add_column("Confidence", width=12)
    table.add_column("Title / URL", width=40)

    found_count = 0
    for r in results:
        status_style = "green" if r.status.value == "found" else "red"
        if r.status.value == "found":
            found_count += 1
        table.add_row(
            r.module,
            r.platform or "-",
            r.query[:24],
            f"[{status_style}]{r.status.value}[/{status_style}]",
            r.confidence.value,
            (r.title or r.url)[:40],
        )

    console.print(table)
    console.print(f"\n[bold green]{found_count}[/] hits out of {len(results)} results.\n")


async def run_cli(profile_path: str | None = None, resume_id: str | None = None) -> None:
    """Main CLI entry point."""
    if profile_path:
        console.print(f"[dim]Loading profile from {profile_path}[/dim]")
        profile = load_profile_from_json(profile_path)
    else:
        profile = collect_profile()

    # Check for resumable scan
    if not resume_id:
        sm = StateManager()
        await sm.connect()
        prev = await sm.get_latest_incomplete_session()
        await sm.close()
        if prev:
            console.print(f"[yellow]Found incomplete scan: {prev.scan_id}[/]")
            if Confirm.ask("  Resume this scan?", default=True):
                resume_id = prev.scan_id

    scanner = Scanner(profile, resume_scan_id=resume_id)
    results = await scanner.run()
    display_results(results)
