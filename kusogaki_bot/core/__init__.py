"""
Core module for Kusogaki Bot.
Contains essential bot functionality and base classes.
"""

from kusogaki_bot.base_cog import BaseCog
from kusogaki_bot.db import Database
from kusogaki_bot.exceptions import BotError, DatabaseError

__all__ = ['Database', 'BaseCog', 'BotError', 'DatabaseError']
