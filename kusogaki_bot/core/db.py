import logging
import os

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

import config
from kusogaki_bot.core.exceptions import DatabaseConnectionError


class DatabaseConfig:
    """
    Configuration settings for database connections
    """

    MIN_POOL_SIZE = 2
    MAX_POOL_SIZE = 5
    MAX_OVERFLOW = 10
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 1800

    SERVER_SELECTION_TIMEOUT = 5000


class MongoDatabase:
    """
    Singleton class to manage PostgreSQL database connection
    """

    client: AsyncMongoClient = None
    db: AsyncDatabase = None

    def __init__(self) -> None:
        self.client = None
        self.db = None

    @classmethod
    def connect(cls) -> None:
        """Establish a MongoDB connection with the URI in .env"""

        db_config = DatabaseConfig()

        cls.client = AsyncMongoClient(
            config.MONGO_URI,
            serverSelectionTimeoutMS=db_config.SERVER_SELECTION_TIMEOUT,
            maxPoolSize=db_config.MAX_POOL_SIZE,
            minPoolSize=db_config.MIN_POOL_SIZE,
            retryWrites=True,
        )

        cls.db = cls.client[config.DB_NAME]

        logging.info('Database Connection Successfull!')

    @classmethod
    def get_db(cls) -> AsyncDatabase:
        """
        Get database connection using singleton pattern

        Returns:
            AsyncDatabase: Async Database Connection

        Raises:
            ServerSelectionTimeoutError: If MongoDB server not found in given time
            ConnectionFailure: If connection cannot be established
        """

        if cls.db is None:
            database_url = os.getenv('DATABASE_URL')

            if not database_url:
                raise DatabaseConnectionError('DATABASE_URL environment variable is not set')

            try:
                cls.connect()
                logging.info('Successfully connected to MongoDB database')

            except ServerSelectionTimeoutError as e:
                logging.error('Failed to connect to MongoDB: Server selection timeout')
                raise ServerSelectionTimeoutError(f'Cound not connect to MongoDB server in given time. {e}')
            except ConnectionFailure as e:
                logging.error(f'Failed to connect to MongoDB: {e}')
                raise ConnectionFailure(f'MongoDB connection Failed {e}')
            except Exception as e:
                logging.error(f'Unexpected error connecting to MongoDB: {e}')
                raise

        return cls.db

    @classmethod
    def close_db(cls) -> None:
        """
        Close all database connections

        Raises:
            DatabaseConnectionError: If connections cannot be closed properly
        """

        if cls.client is None:
            logging.error("MongoDB client session doesn't exist")
            return None

        try:
            cls.client.close()
            cls.client = None
            cls.db = None
        except Exception as e:
            raise DatabaseConnectionError('Could not close the mongoDB connection!') from e

        logging.info('MongoDB connection closed!')
