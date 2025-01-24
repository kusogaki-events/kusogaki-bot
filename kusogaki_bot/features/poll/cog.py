import asyncio
import logging

from discord.ext import commands

from kusogaki_bot.core import BaseCog, KusogakiBot
from kusogaki_bot.features.poll.service import PollError, PollService
from kusogaki_bot.shared import check_permission


class PollCog(BaseCog):
    """
    Cog for basic poll command
    """

    def __init__(self, bot: KusogakiBot):
        super().__init__(bot)
        self.poll_service = PollService()

    @commands.command(name='poll', description='Create a new poll')
    async def create_poll(
        self,
        ctx: commands.Context,
        question: str,
        duration: int,
        multiple: bool,
        *options: str,
    ):
        """Create a new poll. Can be used by staff/dev team

        Args:
            ctx (commands.Context): The command context
            question (str): The question you want to ask
            duration (int): The duration of the poll (hours)
            multiple (bool): Whether to allow multiple options
        """

        if not await check_permission(ctx):
            return await ctx.send("You can only create polls if you're a staff member.")

        try:
            self.poll_service.validate_options(options)
            poll = self.poll_service.create_poll(question, duration, multiple, options)
            poll_message = await ctx.send(poll=poll)
            self.poll_service.add_poll(question, poll, poll_message)
            self.bot.loop.create_task(
                self._remove_poll_after_expiry(question, duration)
            )
        except PollError as e:
            await ctx.send(str(e))

    @commands.command(name='endpoll', description='End an active poll')
    async def end_poll(self, ctx: commands.Context, *, question: str):
        """End an active poll."""

        if not await check_permission(ctx):
            return await ctx.send("You can only end polls if you're a staff member.")

        try:
            poll, _ = self.poll_service.get_poll(question)
            await poll.end()
            await ctx.send(f"Poll '{question}' has been ended successfully.")
            self.poll_service.remove_poll(question)
        except PollError as e:
            await ctx.send(str(e))
        except Exception as e:
            logging.error(f'Error ending poll: {str(e)}', exc_info=True)
            await ctx.send('An error occurred while ending the poll.')

    @commands.command(name='listpolls', description='List all active polls')
    async def list_polls(self, ctx: commands.Context):
        """List all active polls."""

        polls_list = self.poll_service.list_active_polls()
        await ctx.send(polls_list)

    async def _remove_poll_after_expiry(self, question: str, duration: int):
        """Remove poll after it expires."""
        await asyncio.sleep(duration * 3600)
        self.poll_service.remove_poll(question)


async def setup(bot: KusogakiBot):
    await bot.add_cog(PollCog(bot))
