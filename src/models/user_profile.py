"""UserProfile schema for dynamic, multi-value OSINT input."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """Flexible profile that accepts unlimited variations of personal data.

    Every field is an optional list of strings, allowing the user to supply
    as many (or as few) data points as they have.  The cross-correlation
    engine will later generate search permutations from these fields.
    """

    # Identity
    first_names: list[str] = Field(default_factory=list, description="Legal or common first names")
    last_names: list[str] = Field(default_factory=list, description="Legal or maiden last names")
    full_names: list[str] = Field(default_factory=list, description="Full name variations")
    nicknames: list[str] = Field(default_factory=list, description="Online handles, aliases, screen names")

    # Contact
    emails: list[str] = Field(default_factory=list, description="Email addresses (current and past)")
    phone_numbers: list[str] = Field(default_factory=list, description="Phone numbers in any format")

    # Online presence
    usernames: list[str] = Field(default_factory=list, description="Platform usernames / handles")
    domains: list[str] = Field(default_factory=list, description="Personal or business domains")
    social_urls: list[str] = Field(default_factory=list, description="Known social-media profile URLs")

    # Geographic
    birth_cities: list[str] = Field(default_factory=list, description="City / town of birth")
    current_cities: list[str] = Field(default_factory=list, description="Current city / town")
    past_addresses: list[str] = Field(default_factory=list, description="Previous addresses or neighborhoods")
    countries: list[str] = Field(default_factory=list, description="Countries of residence")

    # Education & Work
    schools: list[str] = Field(default_factory=list, description="Schools, high schools, universities")
    workplaces: list[str] = Field(default_factory=list, description="Companies or organizations")
    job_titles: list[str] = Field(default_factory=list, description="Job titles / roles")

    # Personal / Miscellaneous
    birth_dates: list[str] = Field(default_factory=list, description="Date of birth variations (YYYY-MM-DD, etc.)")
    pet_names: list[str] = Field(default_factory=list, description="Pet names (common password / username material)")
    hobbies: list[str] = Field(default_factory=list, description="Interests, hobbies, fandoms")
    keywords: list[str] = Field(default_factory=list, description="Free-form keywords for open-ended search")

    # Catch-all for arbitrary key-value pairs the user wants to add
    custom_fields: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Arbitrary extra fields: {'field_name': ['value1', 'value2']}",
    )

    def all_values(self) -> list[str]:
        """Return a flat, deduplicated list of every data point in the profile."""
        values: list[str] = []
        for field_name in type(self).model_fields:
            raw = getattr(self, field_name)
            if isinstance(raw, list):
                values.extend(raw)
            elif isinstance(raw, dict):
                for lst in raw.values():
                    values.extend(lst)
        return list(dict.fromkeys(values))  # deduplicate, preserve order

    def populated_field_names(self) -> list[str]:
        """Return names of fields that have at least one value."""
        names: list[str] = []
        for field_name in type(self).model_fields:
            raw = getattr(self, field_name)
            if isinstance(raw, list) and raw:
                names.append(field_name)
            elif isinstance(raw, dict) and raw:
                names.append(field_name)
        return names
