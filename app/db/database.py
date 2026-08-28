import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from app.core import settings, logger

class DatabaseManager:
    """Manages SQLite database connections and table initialization."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Creates and configures a new SQLite connection with WAL mode and row factory."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=10.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager providing thread-safe transaction execution and auto-commit/rollback."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error during transaction: {e}")
            raise e
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    def init_db(self):
        """Initializes database schema if tables do not exist."""
        with self.get_cursor() as cursor:
            # Table: daily_counts (aggregate daily totals)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_counts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    in_count INTEGER NOT NULL DEFAULT 0,
                    out_count INTEGER NOT NULL DEFAULT 0,
                    net_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_counts_date ON daily_counts(date);")

            # Table: count_events (individual crossing audit events)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS count_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    date TEXT NOT NULL,
                    direction TEXT NOT NULL CHECK(direction IN ('IN', 'OUT')),
                    track_id INTEGER,
                    source_id TEXT,
                    frame_number INTEGER
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_count_events_date ON count_events(date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_count_events_timestamp ON count_events(timestamp);")

            # Table: inconsistency_alerts (discrepancy & anomaly notifications)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inconsistency_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    date TEXT NOT NULL,
                    in_count INTEGER NOT NULL,
                    out_count INTEGER NOT NULL,
                    discrepancy INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'WARNING',
                    source_id TEXT,
                    acknowledged INTEGER NOT NULL DEFAULT 0
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inconsistency_date ON inconsistency_alerts(date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inconsistency_timestamp ON inconsistency_alerts(timestamp);")
            logger.info(f"Database initialized successfully at {self.db_path}")

# Global database manager singleton
db_manager = DatabaseManager()
