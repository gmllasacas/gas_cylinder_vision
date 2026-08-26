from app.db.database import DatabaseManager
from app.db.repository import DailyCountRepository

# Global singleton repository instance
db_manager = DatabaseManager()
db_repo = DailyCountRepository(db_manager)

__all__ = ["DatabaseManager", "DailyCountRepository", "db_manager", "db_repo"]

