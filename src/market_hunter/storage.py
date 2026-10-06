import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from market_hunter.models import Listing, Watch, WatchCreate


class Storage:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS listings (
                    id TEXT PRIMARY KEY, source TEXT NOT NULL, url TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS watches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, query TEXT NOT NULL,
                    sources_json TEXT NOT NULL, ship_to TEXT NOT NULL, profile TEXT NOT NULL,
                    max_delivered_price_eur REAL, interval_minutes INTEGER NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
                    last_run_at TEXT, last_match_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS watch_matches (
                    watch_id INTEGER NOT NULL, listing_id TEXT NOT NULL, first_matched_at TEXT NOT NULL,
                    PRIMARY KEY (watch_id, listing_id),
                    FOREIGN KEY (watch_id) REFERENCES watches(id),
                    FOREIGN KEY (listing_id) REFERENCES listings(id)
                );
                """
            )

    def upsert_listings(self, listings: list[Listing]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connection() as conn:
            for listing in listings:
                conn.execute(
                    """
                    INSERT INTO listings(id, source, url, payload_json, first_seen_at, last_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET payload_json = excluded.payload_json, last_seen_at = excluded.last_seen_at
                    """,
                    (listing.id, listing.source, str(listing.url), listing.model_dump_json(), now, now),
                )

    def get_listing(self, listing_id: str) -> Listing | None:
        with self._connection() as conn:
            row = conn.execute("SELECT payload_json FROM listings WHERE id = ?", (listing_id,)).fetchone()
        return Listing.model_validate_json(row["payload_json"]) if row else None

    def create_watch(self, watch: WatchCreate) -> Watch:
        created_at = datetime.now(UTC)
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO watches(name, query, sources_json, ship_to, profile, max_delivered_price_eur,
                                    interval_minutes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    watch.name,
                    watch.query,
                    json.dumps([source.value for source in watch.sources]),
                    watch.ship_to,
                    watch.profile,
                    watch.max_delivered_price_eur,
                    watch.interval_minutes,
                    created_at.isoformat(),
                ),
            )
            watch_id = cursor.lastrowid
        return Watch(id=watch_id, created_at=created_at, **watch.model_dump())

    def list_watches(self) -> list[Watch]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM watches ORDER BY id DESC").fetchall()
        return [self._watch_from_row(row) for row in rows]

    def due_watches(self) -> list[Watch]:
        now = datetime.now(UTC)
        return [
            watch
            for watch in self.list_watches()
            if watch.active
            and (watch.last_run_at is None or (now - watch.last_run_at).total_seconds() >= watch.interval_minutes * 60)
        ]

    def record_watch_run(self, watch_id: int, listings: list[Listing]) -> list[Listing]:
        timestamp = datetime.now(UTC).isoformat()
        new_matches: list[Listing] = []
        with self._connection() as conn:
            for listing in listings:
                was_known = conn.execute(
                    "SELECT 1 FROM watch_matches WHERE watch_id = ? AND listing_id = ?", (watch_id, listing.id)
                ).fetchone()
                if not was_known:
                    conn.execute(
                        "INSERT INTO watch_matches(watch_id, listing_id, first_matched_at) VALUES (?, ?, ?)",
                        (watch_id, listing.id, timestamp),
                    )
                    new_matches.append(listing)
            conn.execute(
                "UPDATE watches SET last_run_at = ?, last_match_count = ? WHERE id = ?",
                (timestamp, len(listings), watch_id),
            )
        return new_matches

    @staticmethod
    def _watch_from_row(row: sqlite3.Row) -> Watch:
        data = dict(row)
        data["sources"] = json.loads(data.pop("sources_json"))
        data["active"] = bool(data["active"])
        return Watch.model_validate(data)
