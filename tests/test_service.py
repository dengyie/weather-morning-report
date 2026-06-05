from datetime import timedelta

import pytest

from weather_morning_report.cache import SnapshotCache
from weather_morning_report.providers.base import ProviderError
from weather_morning_report.providers.wttr import parse_wttr_payload
from weather_morning_report.service import load_snapshot
from test_wttr_provider import FETCHED_AT, SHANGHAI, payload


class StubProvider:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    def fetch(self):
        if self.error:
            raise self.error
        return self.result


def weather_snapshot():
    return parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )


def test_successful_provider_result_is_cached(tmp_path) -> None:
    cache = SnapshotCache(tmp_path / "weather.json", timedelta(hours=12))
    snapshot = weather_snapshot()

    result = load_snapshot(StubProvider(result=snapshot), cache, FETCHED_AT)

    assert result.snapshot == snapshot
    assert result.cached is False
    assert cache.load(FETCHED_AT) == snapshot


def test_provider_failure_uses_valid_cache(tmp_path) -> None:
    cache = SnapshotCache(tmp_path / "weather.json", timedelta(hours=12))
    snapshot = weather_snapshot()
    cache.save(snapshot)

    result = load_snapshot(
        StubProvider(error=ProviderError("offline")),
        cache,
        FETCHED_AT + timedelta(hours=6),
    )

    assert result.snapshot == snapshot
    assert result.cached is True


def test_provider_failure_rejects_stale_cache(tmp_path) -> None:
    cache = SnapshotCache(tmp_path / "weather.json", timedelta(hours=12))
    cache.save(weather_snapshot())

    with pytest.raises(ProviderError, match="cache is unavailable.*stale"):
        load_snapshot(
            StubProvider(error=ProviderError("offline")),
            cache,
            FETCHED_AT + timedelta(hours=13),
        )

