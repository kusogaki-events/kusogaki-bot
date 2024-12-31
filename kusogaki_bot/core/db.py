import logging
import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

Base = declarative_base()


class Database:
    """Singleton class to manage PostgreSQL database connection."""

    _instance = None

    @classmethod
    @lru_cache(maxsize=1)
    def get_instance(cls):
        """Get database connection instance using singleton pattern."""
        if cls._instance is None:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError('DATABASE_URL environment variable is not set')

            try:
                if database_url.startswith('postgres://'):
                    database_url = database_url.replace(
                        'postgres://', 'postgresql://', 1
                    )

                engine = create_engine(
                    database_url,
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=1800,
                )

                cls._instance = sessionmaker(bind=engine)
                Base.metadata.create_all(engine)
                logging.info('Successfully connected to PostgreSQL database')
            except Exception as e:
                logging.error(f'Failed to connect to PostgreSQL: {str(e)}')
                raise

        return cls._instance()

    @classmethod
    def close(cls):
        """Close all database connections."""
        if cls._instance is not None:
            try:
                engine = cls._instance.kw['bind']
                engine.dispose()
                cls._instance = None
                cls.get_instance.cache_clear()
                logging.info('Database connections closed')
            except Exception as e:
                logging.error(f'Error closing database connections: {str(e)}')
