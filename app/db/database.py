import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator
from app.core import settings, logger

class DatabaseManager:
    """Thread-safe SQLite Database Manager for gas_stream."""

    def __init__(self, db_path: str = settings.db_path):
        self.db_path = db_path
        self._lock = threading.Lock()
        
        # Ensure database directory exists
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with WAL mode enabled."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode and foreign keys for high concurrent throughput
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Thread-safe context manager providing a transactional cursor."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error during transaction: {e}")
                raise
            finally:
                cursor.close()
                conn.close()

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
            logger.info(f"Database initialized successfully at {self.db_path}")

