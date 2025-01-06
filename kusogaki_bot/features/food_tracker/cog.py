from discord import File, Message
from discord.ext import commands

from config import AWAIZ_USER_ID
from kusogaki_bot.core import BaseCog, KusogakiBot
from kusogaki_bot.features.food_tracker.service import FoodCounterService
from kusogaki_bot.shared import EmbedType


class FoodCounterCog(BaseCog):
    """Cog for tracking food mentions by users"""

    def __init__(self, bot: KusogakiBot):
        super().__init__(bot)
        self.service = FoodCounterService()

    async def is_command(self, message: Message) -> bool:
        """Check if message content starts with any command prefix"""
        prefixes = await self.bot.get_prefix(message)
        if isinstance(prefixes, str):
            return message.content.startswith(prefixes)
        return any(message.content.startswith(prefix) for prefix in prefixes)

    async def send_food_mention_embed(self, channel, user, count: int):
        """Create and send food mention embed"""
        description = f"""
{user.mention}, your caseoh is showing! Adding to the total amount of times you've mentioned food.

**Total is now**: {count}
        """

        embed, _ = await self.create_embed(
            EmbedType.NORMAL, 'Awaiz has mentioned food!', description
        )

        file = File('static/caseoh.png', filename='caseoh.png')
        embed.set_thumbnail(url='attachment://caseoh.png')

        await channel.send(embed=embed, file=file)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages containing food mentions"""
        if message.author.bot or await self.is_command(message):
            return

        if str(message.author.id) != AWAIZ_USER_ID:
            return

        if self.service.check_message_for_food(message.content):
            count = self.service.increment_counter(AWAIZ_USER_ID)
            await self.send_food_mention_embed(message.channel, message.author, count)

    @commands.command(name='awaiz', aliases=['caseoh'])
    async def food_mention(self, ctx: commands.Context):
        """Increment food mention counter for Awaiz"""
        awaiz = await self.bot.fetch_user(AWAIZ_USER_ID)
        if not awaiz:
            return

        count = self.service.increment_counter(AWAIZ_USER_ID)
        await self.send_food_mention_embed(ctx.channel, awaiz, count)

    @commands.command(name='awaizcount', aliases=['drywall'])
    async def food_count(self, ctx: commands.Context):
        """Display food mention count for Awaiz"""
        awaiz = await self.bot.fetch_user(AWAIZ_USER_ID)
        if not awaiz:
            return

        count = self.service.get_count(AWAIZ_USER_ID)
        description = f"""
He's eaten everything. {awaiz.mention} has talked about food {count} time(s). I guess he'll start eating drywall soon.
            """

        embed, _ = await self.create_embed(
            EmbedType.NORMAL, 'Awaiz Food Counter', description
        )

        file = File('static/drywall.png', filename='drywall.png')
        embed.set_thumbnail(url='attachment://drywall.png')

        await ctx.send(embed=embed, file=file)


async def setup(bot: KusogakiBot):
    await bot.add_cog(FoodCounterCog(bot))
