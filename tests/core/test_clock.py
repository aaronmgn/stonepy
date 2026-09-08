from datetime import UTC, datetime

import pytest

from stonepy._core.clock import FakeClock, system_utc_now


def test_fake_clock_rejects_naive_utc_origin() -> None:
    with pytest.raises(ValueError, match="utc_start must be timezone-aware"):
        FakeClock(utc_start=datetime(2020, 1, 1))


def test_fake_clock_utc_origin_advances() -> None:
    clock = FakeClock(utc_start=datetime(2025, 1, 1, tzinfo=UTC))
    clock.advance(5)
    assert clock.utcnow() == datetime(2025, 1, 1, 0, 0, 5, tzinfo=UTC)
    assert system_utc_now().tzinfo is UTC
