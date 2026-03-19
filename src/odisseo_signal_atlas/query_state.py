"""Persistent query history to avoid redundant X searches."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import QuerySpec
from .normalizers import to_iso


@dataclass(slots=True)
class QueryHistoryStore:
    """Persist completed query windows so historical slices are not re-run."""

    path: Path
    retention_days: int = 30
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path, retention_days: int = 30) -> QueryHistoryStore:
        """Load an existing history file and prune expired entries."""

        store = cls(path=path, retention_days=retention_days)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                store.entries = {
                    signature: value
                    for signature, value in payload.items()
                    if isinstance(signature, str) and isinstance(value, dict)
                }
        store.prune()
        return store

    def should_skip(self, query_spec: QuerySpec, refresh_live_window: bool) -> bool:
        """Return ``True`` when a historical query window has already been executed."""

        if query_spec.is_live_window and refresh_live_window:
            return False
        return query_spec.signature in self.entries

    def mark_complete(self, query_spec: QuerySpec, tweet_count: int) -> None:
        """Record a completed query execution."""

        self.entries[query_spec.signature] = {
            "query": query_spec.query,
            "language": query_spec.language.code,
            "topic_label": query_spec.topic_label,
            "window_label": query_spec.window_label,
            "start_time": to_iso(query_spec.start_time),
            "end_time": to_iso(query_spec.end_time),
            "is_live_window": query_spec.is_live_window,
            "tweet_count": tweet_count,
            "executed_at": to_iso(datetime.now(UTC)),
        }

    def prune(self) -> None:
        """Drop stale query history entries outside the retention horizon."""

        cutoff = datetime.now(UTC) - timedelta(days=self.retention_days)
        retained: dict[str, dict[str, Any]] = {}
        for signature, payload in self.entries.items():
            executed_at = _parse_datetime(payload.get("executed_at"))
            if executed_at is None or executed_at >= cutoff:
                retained[signature] = payload
        self.entries = retained

    def save(self) -> None:
        """Persist the current query history to disk."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _parse_datetime(value: Any) -> datetime | None:
    """Parse cached ISO datetimes."""

    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value)
