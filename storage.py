import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class Watch:
    id: int
    chat_id: int
    checkin: str
    checkout: str
    nights: int
    room_type: str
    enabled: bool
    notify_once: bool


class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._init()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self):
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS watches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    checkin TEXT NOT NULL,
                    checkout TEXT NOT NULL,
                    nights INTEGER NOT NULL,
                    room_type TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    notify_once INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_checked_at TEXT,
                    last_seen_rcnt INTEGER,
                    last_seen_cnt INTEGER
                )
            """)

    def add(self, chat_id: int, checkin: str, nights: int, room_type: str) -> int:
        start = date.fromisoformat(checkin)
        checkout = (start + timedelta(days=nights)).isoformat()
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO watches(chat_id,checkin,checkout,nights,room_type,created_at) VALUES(?,?,?,?,?,?)",
                (chat_id, checkin, checkout, nights, room_type, now),
            )
            return int(cur.lastrowid)

    def list(self, chat_id: int, enabled_only: bool = False) -> list[Watch]:
        sql = "SELECT id,chat_id,checkin,checkout,nights,room_type,enabled,notify_once FROM watches WHERE chat_id=?"
        if enabled_only:
            sql += " AND enabled=1"
        sql += " ORDER BY id"
        with self._connect() as db:
            return [Watch(**{**dict(r), "enabled": bool(r["enabled"]), "notify_once": bool(r["notify_once"])}) for r in db.execute(sql, (chat_id,))]

    def set_enabled(self, chat_id: int, watch_id: int, enabled: bool) -> bool:
        with self._connect() as db:
            cur = db.execute("UPDATE watches SET enabled=? WHERE id=? AND chat_id=?", (int(enabled), watch_id, chat_id))
            return cur.rowcount == 1

    def delete(self, chat_id: int, watch_id: int) -> bool:
        with self._connect() as db:
            cur = db.execute("DELETE FROM watches WHERE id=? AND chat_id=?", (watch_id, chat_id))
            return cur.rowcount == 1

    def record(self, watch_id: int, rcnt: int, cnt: int):
        with self._connect() as db:
            db.execute(
                "UPDATE watches SET last_checked_at=?,last_seen_rcnt=?,last_seen_cnt=? WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), rcnt, cnt, watch_id),
            )

