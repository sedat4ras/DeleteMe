"""TraceCleaner - Digital footprint mapper via OSINT cross-correlation."""

from __future__ import annotations

import argparse
import asyncio
import sys

from src.cli import run_cli


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tracecleaner",
        description="Map a user's digital footprint via OSINT cross-correlation.",
    )
    parser.add_argument(
        "-p", "--profile",
        type=str,
        default=None,
        help="Path to a JSON file containing the UserProfile data.",
    )
    parser.add_argument(
        "-r", "--resume",
        type=str,
        default=None,
        help="Scan ID to resume an incomplete scan.",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for TraceCleaner."""
    args = parse_args()
    try:
        asyncio.run(run_cli(profile_path=args.profile, resume_id=args.resume))
    except KeyboardInterrupt:
        print("\n[!] Scan interrupted. Progress has been saved. Use --resume to continue.")
        sys.exit(1)


if __name__ == "__main__":
    main()
