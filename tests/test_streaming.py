"""
tests/test_streaming.py
-----------------------
Unit and integration tests for real-time streaming engine and live analytical queries.
"""

import time
import pytest
from sqlalchemy import create_engine, text

from src.db import ensure_live_trips_table
from src.streaming import LiveStreamEngine
from src.queries import (
    get_live_stream_stats,
    get_live_recent_feed,
    get_live_active_hotspots,
    get_live_throughput_history,
    get_live_surge_alerts
)


@pytest.fixture
def test_stream_engine(tmp_path):
    """Creates a temporary SQLite database engine for testing streaming."""
    test_db = tmp_path / "test_stream.db"
    engine = create_engine(f"sqlite:///{test_db}", future=True)
    ensure_live_trips_table(engine)
    streamer = LiveStreamEngine(db_target=test_db)
    yield streamer, engine
    streamer.stop_background_streaming()


def test_ensure_live_trips_table(test_stream_engine):
    """Verifies that live_trips table and indexes are created properly."""
    _, engine = test_stream_engine
    with engine.connect() as conn:
        tables = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
        assert "live_trips" in tables


def test_batch_injection(test_stream_engine):
    """Tests synchronous injection of streaming batches and calculations."""
    streamer, engine = test_stream_engine
    inserted = streamer.inject_trips(count=15)
    assert inserted == 15

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM live_trips")).scalar()
        assert count == 15


def test_live_queries_with_data(test_stream_engine):
    """Verifies all live analytical query functions against injected stream data."""
    streamer, engine = test_stream_engine
    streamer.inject_trips(count=20)

    # 1. Stats
    stats = get_live_stream_stats(engine)
    assert stats["total_streamed"] == 20
    assert stats["total_revenue"] > 0
    assert stats["avg_fare"] > 0
    assert stats["active_zones"] > 0

    # 2. Recent feed
    feed_df = get_live_recent_feed(engine, limit=10)
    assert len(feed_df) == 10
    assert "event_time" in feed_df.columns
    assert "surge_multiplier" in feed_df.columns

    # 3. Active hotspots
    hotspots = get_live_active_hotspots(engine, limit=5)
    assert not hotspots.empty
    assert "live_trips_count" in hotspots.columns

    # 4. Throughput history
    hist = get_live_throughput_history(engine, limit=10)
    assert not hist.empty
    assert "rides_count" in hist.columns


def test_clear_live_buffer(test_stream_engine):
    """Verifies clearing the streaming buffer."""
    streamer, engine = test_stream_engine
    streamer.inject_trips(count=10)
    streamer.clear_live_buffer()

    stats = get_live_stream_stats(engine)
    assert stats["total_streamed"] == 0


def test_background_streaming_lifecycle(test_stream_engine):
    """Tests starting, running, and cleanly stopping the background streamer."""
    streamer, engine = test_stream_engine
    assert not streamer.is_streaming_active()

    # Start streaming at 20 rides/sec
    started = streamer.start_background_streaming(rate_per_sec=20.0)
    assert started is True
    assert streamer.is_streaming_active() is True

    # Allow background thread to produce trips
    time.sleep(1.2)

    stopped = streamer.stop_background_streaming()
    assert stopped is True
    assert streamer.is_streaming_active() is False

    stats = get_live_stream_stats(engine)
    assert stats["total_streamed"] > 5
