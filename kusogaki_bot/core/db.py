import logging
import os
from functools import lru_cache
from typing import Optional, Type

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from kusogaki_bot.core.exceptions import DatabaseConnectionError

Base = declarative_base()


class DatabaseConfig:
    """
    Configuration settings for database connections
    """

    POOL_SIZE = 5
    MAX_OVERFLOW = 10
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 1800


class Database:
    """
    Singleton class to manage PostgreSQL database connection
    """

    _instance: Optional[Type[Session]] = None

    @classmethod
    @lru_cache(maxsize=1)
    def get_instance(cls) -> Session:
        """
        Get database connection instance using singleton pattern

        Returns:
            Session: SQLAlchemy session instance

        Raises:
            DatabaseConnectionError: If connection cannot be established
        """

        if cls._instance is None:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise DatabaseConnectionError(
                    'DATABASE_URL environment variable is not set'
                )

            try:
                if database_url.startswith('postgres://'):
                    database_url = database_url.replace(
                        'postgres://', 'postgresql://', 1
                    )

                engine = create_engine(
                    database_url,
                    poolclass=QueuePool,
                    pool_size=DatabaseConfig.POOL_SIZE,
                    max_overflow=DatabaseConfig.MAX_OVERFLOW,
                    pool_timeout=DatabaseConfig.POOL_TIMEOUT,
                    pool_recycle=DatabaseConfig.POOL_RECYCLE,
                )

                cls._instance = sessionmaker(bind=engine)
                Base.metadata.create_all(engine)

                logging.info('Successfully connected to PostgreSQL database')
            except Exception as e:
                error_msg = f'Failed to connect to PostgreSQL: {str(e)}'
                logging.error(error_msg)
                raise DatabaseConnectionError(error_msg) from e

        return cls._instance()

    @classmethod
    def close(cls) -> None:
        """
        Close all database connections

        Raises:
            DatabaseConnectionError: If connections cannot be closed properly
        """
        if cls._instance is not None:
            try:
                engine = cls._instance.kw['bind']
                engine.dispose()
                cls._instance = None
                cls.get_instance.cache_clear()

                logging.info('Database connections closed')
            except Exception as e:
                error_msg = f'Error closing database connections: {str(e)}'
                logging.error(error_msg)
                raise DatabaseConnectionError(error_msg) from e

    def __init__(self):
        """Initialize the database instance"""
        self._session = None

    def __enter__(self) -> Session:
        """Enter context manager and create a new session

        Returns:
            Session: SQLAlchemy session instance
        """
        self._session = self.get_instance()
        return self._session

    def __exit__(self, _, __, ___) -> None:
        """Exit context manager and ensure session is closed"""
        if self._session is not None:
            self._session.close()
            self._session = None
