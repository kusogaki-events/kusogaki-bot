import logging

from discord.ext import commands

from kusogaki_bot.core.bot import KusogakiBot
from kusogaki_bot.shared.utils.embeds import EmbedType, get_embed

logger = logging.getLogger(__name__)


class BaseCog(commands.Cog):
    """Base cog class that all other cogs should inherit from"""

    def __init__(self, bot: KusogakiBot) -> None:
        """
        Initialize the base cog

        Args:
            bot (KusogakiBot): The bot instance
        """
        self.bot = bot
        logger.info(f'Initialized {self.__class__.__name__}')

    async def create_embed(self, type: EmbedType, title: str, description: str):
        """
        Helper method to create embeds consistently across cogs

        Args:
            type (EmbedType): The type of embed
            title (str): The embed title
            description (str): The embed description
        """
        return await get_embed(type, title, description)

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """
        Local error handler for all commands in this cog

        Args:
            ctx (commands.Context): The command context
            error (Exception): The error that was raised
        """
        embed, file = await self.create_embed(EmbedType.ERROR, 'Error', str(error))

        await ctx.send(embed=embed, file=file)
        logger.error(f'Error in {ctx.command.name}: {str(error)}')
