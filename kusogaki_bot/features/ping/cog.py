from discord.ext import commands

from kusogaki_bot.core import BaseCog, KusogakiBot
from kusogaki_bot.shared import EmbedType


class PingCog(BaseCog):
    """
    Cog for basic ping command to check bot latency
    """

    def __init__(self, bot: KusogakiBot):
        super().__init__(bot)

    @commands.command(name='ping', description="Check the bot's latency")
    async def ping(self, ctx: commands.Context):
        """
        Simple ping command to check if the bot is responsive

        Args:
            ctx (commands.Context): The command context
        """

        latency = round(self.bot.latency * 1000, 2)
        embed, file = await self.create_embed(
            EmbedType.NORMAL, 'Pong! 🏓', f'**Bot latency**: {latency}ms'
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(name='hello', description="Check the bot's latency")
    async def hello(self, ctx: commands.Context):
        """
        Simple ping command to check if the bot is responsive

        Args:
            ctx (commands.Context): The command context
        """

        latency = round(self.bot.latency * 1000, 2)
        embed, file = await self.create_embed(
            EmbedType.NORMAL, 'Goodbye! 👋', f'**Bot latency**: {latency}ms'
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(name='cheat', description="Check the bot's latency")
    async def cheat(self, ctx: commands.Context):
        """
        Simple ping command to check if the bot is responsive

        Args:
            ctx (commands.Context): The command context
        """

        embed, file = await self.create_embed(
            EmbedType.NORMAL,
            'You have better ping than Nasa 🧑‍🚀',
            '**Bot latency**: 00.01ms',
        )

        await ctx.send(embed=embed, file=file)


async def setup(bot: KusogakiBot):
    await bot.add_cog(PingCog(bot))
