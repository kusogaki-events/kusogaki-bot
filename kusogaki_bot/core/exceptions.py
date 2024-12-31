"""
Core exceptions for Kusogaki Bot.
"""


class BotError(Exception):
    """Base exception for all bot-related errors."""

    pass


class DatabaseError(BotError):
    """Exception raised for database-related errors."""

    pass


class ConfigurationError(BotError):
    """Exception raised for configuration-related errors."""

    pass


class ValidationError(BotError):
    """Exception raised for validation errors."""

    pass


class PermissionError(BotError):
    """Exception raised for permission-related errors."""

    pass


class ServiceError(BotError):
    """Base exception for service-related errors."""

    pass
