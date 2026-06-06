import json
from datetime import timedelta

import pytest

from weather_morning_report.cache import CacheError, SnapshotCache
from weather_morning_report.providers.wttr import parse_wttr_payload
from test_wttr_provider import FETCHED_AT, SHANGHAI, payload


def weather_snapshot():
    return parse_wttr_payload(
        payload(),
        location_name="Changning District, Shanghai",
        timezone=SHANGHAI,
        source="fixture",
        fetched_at=FETCHED_AT,
    )


def test_cache_round_trip_preserves_normalized_snapshot(tmp_path) -> None:
    cache = SnapshotCache(tmp_path / "weather.json", timedelta(hours=12))
    snapshot = weather_snapshot()

    cache.save(snapshot)
    restored = cache.load(FETCHED_AT + timedelta(hours=2))

    assert restored == snapshot


def test_cache_writer_preserves_schema_one_rollback_fields(tmp_path) -> None:
    path = tmp_path / "weather.json"
    SnapshotCache(path, timedelta(hours=12)).save(weather_snapshot())

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["schema_version"] == 1
    assert data["location"]["latitude"] is None
    assert data["location"]["longitude"] is None
    assert data["air_quality"] is None
    assert data["warnings"] == []


def test_cache_rejects_snapshot_older_than_max_age(tmp_path) -> None:
    cache = SnapshotCache(tmp_path / "weather.json", timedelta(hours=12))
    cache.save(weather_snapshot())

    with pytest.raises(CacheError, match="stale"):
        cache.load(FETCHED_AT + timedelta(hours=13))


def test_cache_rejects_invalid_schema(tmp_path) -> None:
    path = tmp_path / "weather.json"
    path.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
    cache = SnapshotCache(path, timedelta(hours=12))

    with pytest.raises(CacheError, match="unsupported cache schema"):
        cache.load(FETCHED_AT)


def test_cache_ignores_legacy_phase_two_fields(tmp_path) -> None:
    path = tmp_path / "weather.json"
    cache = SnapshotCache(path, timedelta(hours=12))
    snapshot = weather_snapshot()
    cache.save(snapshot)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["location"].update({"latitude": 31.22, "longitude": 121.42})
    data["air_quality"] = None
    data["warnings"] = []
    path.write_text(json.dumps(data), encoding="utf-8")

    assert cache.load(FETCHED_AT + timedelta(hours=2)) == snapshot


def test_cache_reports_missing_snapshot(tmp_path) -> None:
    cache = SnapshotCache(tmp_path / "missing.json", timedelta(hours=12))

    with pytest.raises(CacheError, match="does not exist"):
        cache.load(FETCHED_AT)
