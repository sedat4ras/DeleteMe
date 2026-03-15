"""Tests for the UserProfile model."""

from src.models.user_profile import UserProfile


def test_empty_profile():
    profile = UserProfile()
    assert profile.all_values() == []
    assert profile.populated_field_names() == []


def test_basic_fields():
    profile = UserProfile(
        first_names=["John", "Johnny"],
        last_names=["Doe"],
        emails=["john@example.com"],
    )
    assert "John" in profile.all_values()
    assert "Johnny" in profile.all_values()
    assert "Doe" in profile.all_values()
    assert "john@example.com" in profile.all_values()
    assert set(profile.populated_field_names()) == {"first_names", "last_names", "emails"}


def test_custom_fields():
    profile = UserProfile(
        first_names=["Jane"],
        custom_fields={"favorite_color": ["blue", "green"]},
    )
    values = profile.all_values()
    assert "Jane" in values
    assert "blue" in values
    assert "green" in values
    assert "custom_fields" in profile.populated_field_names()


def test_deduplication():
    profile = UserProfile(
        first_names=["Alice"],
        nicknames=["Alice"],  # duplicate
    )
    values = profile.all_values()
    assert values.count("Alice") == 1


def test_json_roundtrip():
    profile = UserProfile(
        first_names=["Bob"],
        schools=["MIT"],
        keywords=["python"],
    )
    json_str = profile.model_dump_json()
    restored = UserProfile.model_validate_json(json_str)
    assert restored.first_names == ["Bob"]
    assert restored.schools == ["MIT"]
