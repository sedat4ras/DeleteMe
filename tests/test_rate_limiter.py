"""Tests for the rate limiter."""

import asyncio

import pytest

from src.core.rate_limiter import RateLimiter, random_user_agent


def test_random_user_agent():
    ua = random_user_agent()
    assert isinstance(ua, str)
    assert "Mozilla" in ua


def test_initial_delay():
    limiter = RateLimiter(base_delay=2.0)
    assert limiter.get_delay("example.com") == 2.0


def test_backoff_on_failure():
    limiter = RateLimiter(base_delay=1.0, backoff_factor=2.0)
    limiter.report_failure("api.example.com")
    assert limiter.get_delay("api.example.com") == 2.0
    limiter.report_failure("api.example.com")
    assert limiter.get_delay("api.example.com") == 4.0


def test_reset_on_success():
    limiter = RateLimiter(base_delay=1.0, backoff_factor=2.0)
    limiter.report_failure("api.example.com")
    limiter.report_failure("api.example.com")
    limiter.report_success("api.example.com")
    assert limiter.get_delay("api.example.com") == 1.0


def test_max_delay_cap():
    limiter = RateLimiter(base_delay=1.0, max_delay=10.0, backoff_factor=3.0)
    for _ in range(20):
        limiter.report_failure("slow.com")
    assert limiter.get_delay("slow.com") == 10.0


def test_per_domain_isolation():
    limiter = RateLimiter(base_delay=1.0, backoff_factor=2.0)
    limiter.report_failure("a.com")
    assert limiter.get_delay("a.com") == 2.0
    assert limiter.get_delay("b.com") == 1.0  # unaffected
