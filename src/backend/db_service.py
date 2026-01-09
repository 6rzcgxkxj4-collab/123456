"""
Database service for managing database connections and sessions.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from src.models.database import Base
from config.config import config


class DatabaseService:
    """Service class for database operations."""
    
    def __init__(self, database_uri: str = None):
        """
        Initialize database service.
        
        Args:
            database_uri: Database connection URI. Defaults to config value.
        """
        self.database_uri = database_uri or config.DATABASE_URI
        self.engine = create_engine(self.database_uri, echo=False)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(self.engine)
    
    def drop_tables(self):
        """Drop all database tables."""
        Base.metadata.drop_all(self.engine)
    
    def get_session(self):
        """Get a new database session."""
        return self.Session()
    
    def close_session(self):
        """Close the current session."""
        self.Session.remove()


# Create default database service instance
db_service = DatabaseService()
