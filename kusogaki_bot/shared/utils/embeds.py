from datetime import datetime
from enum import Enum

from discord import Embed, File


class EmbedColor(int, Enum):
    NORMAL = 0x2B2D31
    INFORMATION = 0x546E7A
    WARNING = 0xE67E22
    ERROR = 0xE74C3C


class EmbedType(Enum):
    NORMAL = EmbedColor.NORMAL
    INFORMATION = EmbedColor.INFORMATION
    WARNING = EmbedColor.WARNING
    ERROR = EmbedColor.ERROR


async def get_embed(type: EmbedType, title: str, description: str) -> Embed:
    """
    Create a Discord embed with specified type, title, and description.

    Args:
        type (EmbedType): The type of embed which determines its color
        title (str): The embed title
        description (str): The embed description
        thumbnail (bool, optional): Whether to include a thumbnail. Defaults to False

    Returns:
        Embed: A configured Discord embed
    """
    embed = Embed(
        title=title,
        description=description,
        color=type.value.value,
        timestamp=datetime.now(),
    )

    file = File('static/fern-pout.png', filename='fern-pout.png')
    embed.set_thumbnail(url='attachment://fern-pout.png')

    return embed, file
