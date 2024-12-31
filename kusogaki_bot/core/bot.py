"""
Core bot setup and configuration.
"""

import logging
from os import listdir
from os.path import isdir

import discord
from discord.ext import commands

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class KusogakiBot(commands.AutoShardedBot):
    """Main bot class with core functionality."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=self.get_prefix, intents=intents, help_command=None
        )

    async def get_prefix(self, message):
        """Get the command prefix for the bot."""
        return commands.when_mentioned_or('kuso ', 'KUSO ', 'Kuso ')(self, message)

    async def load_features(self):
        """Load all feature modules."""
        try:
            feature_dir = 'kusogaki_bot/features'
            for feature in listdir(feature_dir):
                if not feature.startswith('__'):
                    feature_path = f'{feature_dir}/{feature}'
                    if isdir(feature_path):
                        try:
                            await self.load_extension(
                                f'kusogaki_bot.features.{feature}.cog'
                            )
                            logger.info(f'Loaded feature: {feature}')
                        except Exception as e:
                            logger.error(f'Failed to load feature {feature}: {e}')
                            raise ConfigurationError(
                                f'Failed to load feature {feature}: {str(e)}'
                            )
        except Exception as e:
            logger.error(f'Error loading features: {e}')
            raise ConfigurationError(f'Feature loading failed: {str(e)}')

    async def setup_hook(self) -> None:
        """Setup hook called when the bot is starting up."""
        await self.load_features()

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'Logged in as {self.user.name}')
