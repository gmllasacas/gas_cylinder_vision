import sqlite3
import os
import threading
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, List
from app.core import settings, logger

class DatabaseManager:
    """Manages SQLite database connections and table initialization with thread-local pooling."""

    def __init__(self, db_path: str = None):
        self._local = threading.local()
        self._open_connections: List[sqlite3.Connection] = []
        self._pool_lock = threading.Lock()
        self.db_path = db_path or settings.db_path
        self.init_db()

    @property
    def db_path(self) -> str:
        return self._db_path

    @db_path.setter
    def db_path(self, value: str):
        new_path = str(value) if value else settings.db_path
        if hasattr(self, "_db_path") and self._db_path != new_path:
            self.close()
        self._db_path = new_path
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _create_connection(self) -> sqlite3.Connection:
        """Instantiates a single configured SQLite connection."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=15.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        with self._pool_lock:
            self._open_connections.append(conn)
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Returns a cached thread-local connection or instantiates a new one."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.total_changes
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                conn = None

        if conn is None:
            conn = self._create_connection()
            self._local.conn = conn
        return conn

    def close(self):
        """Closes all cached connections opened by this DatabaseManager."""
        with self._pool_lock:
            for conn in self._open_connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._open_connections.clear()
        if hasattr(self._local, "conn"):
            self._local.conn = None

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
            except Exception:
                pass

    def init_db(self):
        """Initializes database schema and persistent WAL journal mode."""
        with self.get_cursor() as cursor:
            # Set WAL mode once persistently for the database file
            cursor.execute("PRAGMA journal_mode=WAL;")

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
