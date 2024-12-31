import logging
from typing import Optional

import discord
from discord.ext import commands

from kusogaki_bot.services.poll_service import PollError
from kusogaki_bot.services.reminder_service import ReminderError
from kusogaki_bot.utils.embeds import EmbedType, get_embed
from kusogaki_bot.utils.permissions import MissingRequiredRole

logger = logging.getLogger(__name__)


class BaseCog(commands.Cog):
    """Base cog class with common error handling."""

    service_errors = [PollError, ReminderError]

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        """Handle common errors for all cogs."""
        error = getattr(error, 'original', error)

        try:
            if isinstance(error, MissingRequiredRole):
                await ctx.send(str(error))
                return

            if any(isinstance(error, err_type) for err_type in self.service_errors):
                await ctx.send(str(error))
                return

            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f'Missing required argument: `{error.param.name}`')
                return

            if isinstance(error, commands.BadArgument):
                await ctx.send(f'Invalid argument provided: {str(error)}')
                return

            if isinstance(error, commands.CommandOnCooldown):
                minutes, seconds = divmod(int(error.retry_after), 60)
                time_str = f'{minutes}m {seconds}s' if minutes else f'{seconds}s'
                await ctx.send(f'This command is on cooldown. Try again in {time_str}')
                return

            if isinstance(error, commands.MissingPermissions):
                await ctx.send(
                    "You don't have the required permissions to use this command."
                )
                return

            if isinstance(error, commands.DisabledCommand):
                await ctx.send('This command is currently disabled.')
                return

            if isinstance(error, commands.NoPrivateMessage):
                await ctx.send("This command can't be used in private messages.")
                return

            if isinstance(error, commands.NotOwner):
                await ctx.send('This command can only be used by the bot owner.')
                return

            if isinstance(error, ValueError):
                await ctx.send(str(error))
                return

            logger.error(
                f'Unexpected error in {ctx.command} invoked by {ctx.author} (ID: {ctx.author.id}): {str(error)}',
                exc_info=error,
            )
            await ctx.send('An unexpected error occurred. Please try again later.')

        except Exception as e:
            logger.error(f'Error in error handler: {str(e)}', exc_info=True)
            await ctx.send('An error occurred while handling the error.')

    async def get_error_embed(
        self, error: Exception, title: Optional[str] = None
    ) -> discord.Embed:
        """Create a standard error embed."""
        return await get_embed(EmbedType.ERROR, title or 'Error', str(error))

    @staticmethod
    def format_error_message(error: Exception, command_name: str) -> str:
        """Format an error message for a specific command."""
        if isinstance(error, commands.MissingRequiredArgument):
            return f'Missing argument for `{command_name}`: {error.param.name}'
        return str(error)
