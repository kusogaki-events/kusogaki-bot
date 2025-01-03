class BotError(Exception):
    """Base exception for all bot-related errors."""

    pass


class DatabaseError(BotError):
    """Exception raised for database-related errors."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Custom exception for database connection errors"""

    pass
