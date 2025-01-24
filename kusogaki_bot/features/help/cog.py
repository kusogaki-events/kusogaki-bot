from typing import Optional

from discord.ext import commands

from kusogaki_bot.core import BaseCog, KusogakiBot
from kusogaki_bot.features.help.data import HelpView
from kusogaki_bot.features.help.service import HelpService
from kusogaki_bot.shared import EmbedType


class HelpCog(BaseCog):
    def __init__(self, bot: KusogakiBot):
        super().__init__(bot)
        self.help_service = HelpService()

    @commands.command(name='help', description='Get help with bot commands')
    async def help(self, ctx: commands.Context, command: Optional[str] = None):
        if command:
            embed, file = await self.help_service.get_command_help(command)
            if embed:
                await ctx.send(embed=embed, file=file)
            else:
                embed, file = await self.create_embed(
                    EmbedType.ERROR,
                    'Command Not Found',
                    f'The command `{command}` was not found. Use `kuso help` to see all available commands.',
                )
                await ctx.send(embed=embed, file=file)
        else:
            embed, file = await self.help_service.get_overview_embed()
            view = HelpView(self.help_service)
            await ctx.send(embed=embed, file=file, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
