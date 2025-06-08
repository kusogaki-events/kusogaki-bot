from discord import ButtonStyle, Interaction
from discord.ui import Button, View


class MediaRec:
    def __init__(
        self,
        media_id: int,
        title: str,
        score: float = 0,
        genres: list[str] = (),
        cover_url: str = None,
        mean_score: float = None,
    ):
        self.media_id = media_id
        self.title = title
        self.score = score
        self.genres = genres
        self.cover_url = cover_url
        self.mean_score = mean_score

    def __lt__(self, other):
        return self.score < other.score

    def __eq__(self, other):
        return isinstance(other, MediaRec) and other.media_id == self.media_id


class NextRecButton(Button):
    def __init__(self):
        super().__init__(
            style=ButtonStyle.success,
            label='Next',
            custom_id='next_rec',
        )


class PrevRecButton(Button):
    def __init__(self):
        super().__init__(
            style=ButtonStyle.danger,
            label='Prev',
            custom_id='prev_rec',
        )


class RecView(View):
    """
    Discord UI View for handling animanga recommendation interactions.

    Attributes:
        rec_service (RecommendationService): Recommendation service for handling recommendation logic
        anilist_username (str): Anilist username to recommend for
        media_type (str): Specify to recommend manga/anime
        genre (str): Limit recommendations to specified genre
        page (int): Which recommendation in user's rec list to display
    """

    def __init__(self, rec_service, anilist_username: str, media_type: str, genre: str):
        super().__init__(timeout=60)
        self.rec_service = rec_service
        self.add_item(PrevRecButton())
        self.add_item(NextRecButton())
        self.anilist_username = anilist_username
        self.media_type = media_type
        self.genre = genre
        self.page = 0

    async def interaction_check(self, interaction: Interaction) -> bool:
        embed = None
        if interaction.data['custom_id'] == 'prev_rec':
            self.page -= 1
            embed = self.rec_service.get_rec_embed(
                anilist_username=self.anilist_username,
                media_type=self.media_type,
                genre=self.genre,
                page=self.page,
            )
        elif interaction.data['custom_id'] == 'next_rec':
            self.page += 1
            embed = self.rec_service.get_rec_embed(
                anilist_username=self.anilist_username,
                media_type=self.media_type,
                genre=self.genre,
                page=self.page,
            )

        await interaction.response.edit_message(embed=embed, view=self)
        return True
