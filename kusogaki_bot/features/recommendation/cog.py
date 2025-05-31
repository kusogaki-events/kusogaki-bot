from typing import Optional

from discord.ext import commands
from httpx import RequestError

from kusogaki_bot.core import BaseCog, KusogakiBot
from kusogaki_bot.features.recommendation.data import RecView
from kusogaki_bot.features.recommendation.service import RecommendationService


class RecommendationCog(BaseCog):
    def __init__(self, bot: KusogakiBot):
        super().__init__(bot)
        self.recommendation_service = RecommendationService()

    @commands.command(
        name='recommend',
        description='Have the bot recommend a manga/anime.',
        aliases=['rec'],
    )
    async def recommend(
        self,
        ctx: commands.Context,
        anilist_username: str,
        genre: Optional[str] = '',
        media_type: Optional[str] = 'anime',
    ):
        anilist_username = anilist_username.lower()
        genre = genre.lower()
        media_type = media_type.lower()
        if genre in ['anime', 'manga']:
            media_type = genre
            genre = ''

        await ctx.defer()

        try:
            await self.recommendation_service.check_recommendation(
                anilist_username=anilist_username,
                media_type=media_type,
                force_update=False,
            )
        except RequestError:
            await ctx.send('Error obtaining data from Anilist. Please try again later.')

        view = RecView(
            self.recommendation_service,
            anilist_username=anilist_username,
            media_type=media_type,
            genre=genre,
        )
        embed = self.recommendation_service.get_rec_embed(
            anilist_username=anilist_username,
            media_type=media_type,
            genre=genre,
            page=view.page,
        )
        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(RecommendationCog(bot))
