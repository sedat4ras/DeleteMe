"""Cross-correlation engine that generates search permutations from UserProfile fields."""

from __future__ import annotations

from itertools import product
from typing import NamedTuple

from src.models.user_profile import UserProfile


class QueryPermutation(NamedTuple):
    """A generated search query with metadata about its origin fields."""

    query: str
    source_fields: tuple[str, ...]


# Pairs of field names to combine.  Order matters for readability of the
# resulting query string (e.g. "john smithville high" reads better than
# "smithville high john").
CORRELATION_PAIRS: list[tuple[str, ...]] = [
    # Identity x Identity
    ("first_names", "last_names"),
    ("nicknames", "last_names"),
    # Identity x Location
    ("first_names", "birth_cities"),
    ("first_names", "current_cities"),
    ("last_names", "birth_cities"),
    ("nicknames", "birth_cities"),
    ("nicknames", "current_cities"),
    # Identity x Education / Work
    ("first_names", "schools"),
    ("last_names", "schools"),
    ("nicknames", "schools"),
    ("first_names", "workplaces"),
    ("last_names", "workplaces"),
    # Identity x Personal
    ("first_names", "pet_names"),
    ("nicknames", "pet_names"),
    ("nicknames", "hobbies"),
    # Contact-derived (email prefix as pseudo-name)
    ("usernames", "last_names"),
    ("usernames", "birth_cities"),
    ("usernames", "schools"),
    # Three-way combos for higher specificity
    ("first_names", "last_names", "birth_cities"),
    ("first_names", "last_names", "schools"),
    ("first_names", "last_names", "workplaces"),
    ("nicknames", "last_names", "current_cities"),
]


class Correlator:
    """Generates deduplicated search queries from a UserProfile."""

    def __init__(self, profile: UserProfile, extra_pairs: list[tuple[str, ...]] | None = None) -> None:
        self.profile = profile
        self.pairs = list(CORRELATION_PAIRS)
        if extra_pairs:
            self.pairs.extend(extra_pairs)

    def generate(self) -> list[QueryPermutation]:
        """Produce all unique query permutations.

        Returns a deduplicated, sorted list of QueryPermutation objects.
        """
        seen: set[str] = set()
        permutations: list[QueryPermutation] = []

        # 1) Single-value queries (every individual data point is a query on its own)
        for field_name in self.profile.populated_field_names():
            values = getattr(self.profile, field_name)
            if isinstance(values, dict):
                for vals in values.values():
                    for v in vals:
                        self._add(v, (field_name,), seen, permutations)
            else:
                for v in values:
                    self._add(v, (field_name,), seen, permutations)

        # 2) Multi-field cross-correlation
        for field_combo in self.pairs:
            field_values: list[list[str]] = []
            valid = True
            for fname in field_combo:
                raw = getattr(self.profile, fname, None)
                if raw is None or (isinstance(raw, list) and not raw):
                    valid = False
                    break
                field_values.append(raw if isinstance(raw, list) else [])
            if not valid or not all(field_values):
                continue

            for combo in product(*field_values):
                query = " ".join(combo)
                self._add(query, field_combo, seen, permutations)

        # 3) Email prefix extraction — treat the local part as a username
        for email in self.profile.emails:
            prefix = email.split("@")[0] if "@" in email else email
            self._add(prefix, ("emails",), seen, permutations)

        # 4) Full names as-is
        for name in self.profile.full_names:
            self._add(name, ("full_names",), seen, permutations)

        return permutations

    @staticmethod
    def _add(
        query: str,
        source_fields: tuple[str, ...],
        seen: set[str],
        out: list[QueryPermutation],
    ) -> None:
        normalized = query.strip().lower()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        out.append(QueryPermutation(query=query.strip(), source_fields=source_fields))

    def generate_dork_queries(self) -> list[QueryPermutation]:
        """Generate Google-dork-style queries for deeper searches.

        Wraps base permutations in dork operators like site:, inurl:, intitle:.
        """
        base = self.generate()
        dorks: list[QueryPermutation] = []
        seen: set[str] = set()

        social_sites = [
            "linkedin.com", "facebook.com", "twitter.com", "instagram.com",
            "github.com", "reddit.com", "medium.com",
        ]

        for perm in base:
            q = perm.query
            # Exact-match quoted search
            quoted = f'"{q}"'
            self._add(quoted, perm.source_fields, seen, dorks)

            # Site-specific dorks for identity queries
            if any(f in ("first_names", "last_names", "nicknames", "usernames", "full_names")
                   for f in perm.source_fields):
                for site in social_sites:
                    dork = f'site:{site} "{q}"'
                    self._add(dork, perm.source_fields + ("dork",), seen, dorks)

            # inurl dork for usernames
            if "usernames" in perm.source_fields or "nicknames" in perm.source_fields:
                self._add(f"inurl:{q}", perm.source_fields + ("dork",), seen, dorks)

        return dorks
