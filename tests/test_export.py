"""Export shape and idempotency logic. The live check (export twice, totals unchanged)
runs against BigQuery in the deploy smoke step."""

from datetime import UTC, datetime

import pytest

from control_plane.analytics.export import (
    TABLES,
    assert_no_text,
    build_rows,
    merge_sql,
)
from control_plane.analytics.queries import QUERIES, QueryError, check_range
from control_plane.fixtures import seed_registry
from control_plane.store import MemoryStore

NOW = datetime(2026, 10, 12, 12, tzinfo=UTC)


def rows():  # type: ignore[no-untyped-def]
    s = MemoryStore()
    seed_registry(s, NOW)
    s.create(
        "product_events",
        "p1",
        {
            "event_id": "p1",
            "event": "portfolio_viewed",
            "app_id": None,
            "role": "admin",
            "source_view": "portfolio",
            "timestamp": NOW.isoformat(),
        },
    )
    return build_rows(s, NOW)


def test_every_table_builds_with_stable_unique_ids() -> None:
    first, second = rows(), rows()
    assert set(first) == set(TABLES)
    for table, data in first.items():
        ids = [r["event_id"] for r in data]
        assert len(ids) == len(set(ids)), table
        assert sorted(ids) == sorted(r["event_id"] for r in second[table]), table
        for r in data:
            assert r["event_date"] == r["event_ts"][:10]


def test_no_text_reaches_bigquery() -> None:
    for data in rows().values():
        assert_no_text(data)
    with pytest.raises(ValueError):
        assert_no_text([{"event_id": "x", "text": "secret"}])


def test_merge_dedupes_by_event_id_and_upserts() -> None:
    sql = merge_sql("proj", "app_events", ["event_id", "app_id", "event_ts", "event_date"])
    assert "ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY event_ts DESC)" in sql
    assert "WHERE rn = 1" in sql
    assert "ON T.event_id = S.event_id" in sql
    assert "WHEN NOT MATCHED THEN INSERT" in sql and "WHEN MATCHED THEN UPDATE" in sql


def test_queries_are_parameterized_and_range_capped() -> None:
    for name, sql in QUERIES.items():
        assert "@" in sql, name
    check_range(NOW.date().replace(month=5), NOW.date())
    with pytest.raises(QueryError):
        check_range(NOW.date().replace(year=2025), NOW.date())
