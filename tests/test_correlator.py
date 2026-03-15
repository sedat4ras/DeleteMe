"""Tests for the cross-correlation engine."""

from src.core.correlator import Correlator
from src.models.user_profile import UserProfile


def test_single_field_permutations():
    profile = UserProfile(first_names=["Alice", "Bob"])
    correlator = Correlator(profile)
    perms = correlator.generate()
    queries = [p.query for p in perms]
    assert "Alice" in queries
    assert "Bob" in queries


def test_cross_correlation():
    profile = UserProfile(
        first_names=["John"],
        last_names=["Doe"],
    )
    correlator = Correlator(profile)
    perms = correlator.generate()
    queries = [p.query.lower() for p in perms]
    assert "john doe" in queries


def test_email_prefix_extraction():
    profile = UserProfile(emails=["coolhacker42@gmail.com"])
    correlator = Correlator(profile)
    perms = correlator.generate()
    queries = [p.query for p in perms]
    assert "coolhacker42" in queries


def test_deduplication():
    profile = UserProfile(
        first_names=["Same"],
        nicknames=["Same"],
    )
    correlator = Correlator(profile)
    perms = correlator.generate()
    query_list = [p.query.lower() for p in perms]
    assert query_list.count("same") == 1


def test_three_way_combo():
    profile = UserProfile(
        first_names=["Jane"],
        last_names=["Smith"],
        birth_cities=["Boston"],
    )
    correlator = Correlator(profile)
    perms = correlator.generate()
    queries = [p.query.lower() for p in perms]
    assert "jane smith boston" in queries


def test_dork_queries():
    profile = UserProfile(usernames=["testuser"])
    correlator = Correlator(profile)
    dorks = correlator.generate_dork_queries()
    queries = [p.query for p in dorks]
    assert any("site:github.com" in q for q in queries)
    assert any("inurl:testuser" in q for q in queries)


def test_empty_profile_no_crash():
    profile = UserProfile()
    correlator = Correlator(profile)
    assert correlator.generate() == []
    assert correlator.generate_dork_queries() == []
