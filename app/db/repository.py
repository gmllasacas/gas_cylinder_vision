from datetime import datetime
from typing import Optional, List, Dict, Any
from app.core import logger
from app.db.database import DatabaseManager

class DailyCountRepository:
    """Repository handling all CRUD and atomic operations for daily gas cylinder counts."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    @staticmethod
    def _today_str() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat()

    def get_or_create_daily(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """Returns the daily count record for target_date (default: today), creating it if absent."""
        date_val = target_date or self._today_str()
        now = self._now_iso()

        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT date, in_count, out_count, net_count, created_at, updated_at FROM daily_counts WHERE date = ?",
                (date_val,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

            cursor.execute(
                """
                INSERT INTO daily_counts (date, in_count, out_count, net_count, created_at, updated_at)
                VALUES (?, 0, 0, 0, ?, ?)
                ON CONFLICT(date) DO NOTHING
                """,
                (date_val, now, now)
            )

            cursor.execute(
                "SELECT date, in_count, out_count, net_count, created_at, updated_at FROM daily_counts WHERE date = ?",
                (date_val,)
            )
            return dict(cursor.fetchone())

    def record_crossing(
        self,
        direction: str,
        track_id: Optional[int] = None,
        source_id: Optional[str] = None,
        frame_number: Optional[int] = None,
        target_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Atomically records a directional line crossing:
        1. Inserts audit event into count_events.
        2. Upserts/increments daily totals in daily_counts.
        """
        direction = direction.upper()
        if direction not in ("IN", "OUT"):
            raise ValueError(f"Invalid direction '{direction}'. Must be 'IN' or 'OUT'.")

        date_val = target_date or self._today_str()
        now = self._now_iso()

        in_delta = 1 if direction == "IN" else 0
        out_delta = 1 if direction == "OUT" else 0

        with self.db.get_cursor() as cursor:
            # 1. Log event
            cursor.execute(
                """
                INSERT INTO count_events (timestamp, date, direction, track_id, source_id, frame_number)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (now, date_val, direction, track_id, source_id, frame_number)
            )

            # 2. Upsert daily count aggregate
            cursor.execute(
                """
                INSERT INTO daily_counts (date, in_count, out_count, net_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    in_count = daily_counts.in_count + excluded.in_count,
                    out_count = daily_counts.out_count + excluded.out_count,
                    net_count = (daily_counts.in_count + excluded.in_count) - (daily_counts.out_count + excluded.out_count),
                    updated_at = excluded.updated_at
                """,
                (date_val, in_delta, out_delta, in_delta - out_delta, now, now)
            )

            cursor.execute(
                "SELECT date, in_count, out_count, net_count, created_at, updated_at FROM daily_counts WHERE date = ?",
                (date_val,)
            )
            updated_record = dict(cursor.fetchone())
            logger.debug(f"Recorded crossing {direction} for {date_val}: {updated_record}")
            return updated_record

    def set_daily_counts(
        self,
        in_count: int,
        out_count: int,
        target_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Manually synchronizes or overrides counts for a specific date."""
        date_val = target_date or self._today_str()
        now = self._now_iso()
        net_count = in_count - out_count

        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_counts (date, in_count, out_count, net_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    in_count = excluded.in_count,
                    out_count = excluded.out_count,
                    net_count = excluded.net_count,
                    updated_at = excluded.updated_at
                """,
                (date_val, in_count, out_count, net_count, now, now)
            )

            cursor.execute(
                "SELECT date, in_count, out_count, net_count, created_at, updated_at FROM daily_counts WHERE date = ?",
                (date_val,)
            )
            return dict(cursor.fetchone())

    def get_daily_count(self, target_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves count record for a given date, or None if not recorded yet."""
        date_val = target_date or self._today_str()
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT date, in_count, out_count, net_count, created_at, updated_at FROM daily_counts WHERE date = ?",
                (date_val,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_history(
        self,
        limit: int = 30,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves historical daily counts ordered by date descending."""
        query = "SELECT date, in_count, out_count, net_count, created_at, updated_at FROM daily_counts"
        params: List[Any] = []
        conditions = []

        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY date DESC LIMIT ?"
        params.append(max(1, min(limit, 365)))

        with self.db.get_cursor() as cursor:
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def get_events(
        self,
        limit: int = 50,
        target_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves recent crossing event audit logs."""
        query = "SELECT id, timestamp, date, direction, track_id, source_id, frame_number FROM count_events"
        params: List[Any] = []

        if target_date:
            query += " WHERE date = ?"
            params.append(target_date)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))

        with self.db.get_cursor() as cursor:
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def reset_daily_count(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """Resets the count numbers to 0 for a given date."""
        date_val = target_date or self._today_str()
        now = self._now_iso()

        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_counts (date, in_count, out_count, net_count, created_at, updated_at)
                VALUES (?, 0, 0, 0, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    in_count = 0,
                    out_count = 0,
                    net_count = 0,
                    updated_at = excluded.updated_at
                """,
                (date_val, now, now)
            )
            cursor.execute(
                "SELECT date, in_count, out_count, net_count, created_at, updated_at FROM daily_counts WHERE date = ?",
                (date_val,)
            )
            return dict(cursor.fetchone())

    def record_inconsistency(
        self,
        in_count: int,
        out_count: int,
        message: str,
        severity: str = "WARNING",
        source_id: Optional[str] = None,
        target_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Logs an inconsistency/anomaly alert into SQLite."""
        date_val = target_date or self._today_str()
        now = self._now_iso()
        discrepancy = out_count - in_count

        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO inconsistency_alerts (timestamp, date, in_count, out_count, discrepancy, message, severity, source_id, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (now, date_val, in_count, out_count, discrepancy, message, severity, source_id)
            )
            alert_id = cursor.lastrowid
            cursor.execute(
                "SELECT id, timestamp, date, in_count, out_count, discrepancy, message, severity, source_id, acknowledged FROM inconsistency_alerts WHERE id = ?",
                (alert_id,)
            )
            created = dict(cursor.fetchone())
            logger.warning(f"Inconsistency Alert logged [ID={alert_id}]: {message} (IN={in_count}, OUT={out_count})")
            return created

    def get_inconsistency_alerts(
        self,
        limit: int = 50,
        target_date: Optional[str] = None,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieves recent anomaly/inconsistency alerts."""
        query = "SELECT id, timestamp, date, in_count, out_count, discrepancy, message, severity, source_id, acknowledged FROM inconsistency_alerts"
        params: List[Any] = []
        conditions = []

        if target_date:
            conditions.append("date = ?")
            params.append(target_date)
        if unread_only:
            conditions.append("acknowledged = 0")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))

        with self.db.get_cursor() as cursor:
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def clear_inconsistency_alerts(self, target_date: Optional[str] = None) -> int:
        """Clears or marks inconsistency alerts as acknowledged."""
        with self.db.get_cursor() as cursor:
            if target_date:
                cursor.execute("DELETE FROM inconsistency_alerts WHERE date = ?", (target_date,))
            else:
                cursor.execute("DELETE FROM inconsistency_alerts")
            return cursor.rowcount
