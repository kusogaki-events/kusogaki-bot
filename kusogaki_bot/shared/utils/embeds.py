from datetime import datetime
from enum import Enum
from typing import Optional, Tuple

from discord import Embed, File


class EmbedColor(int, Enum):
    NORMAL = 0x6A1B9A
    INFORMATION = 0x546E7A
    WARNING = 0xE67E22
    ERROR = 0xE74C3C


class EmbedType(Enum):
    NORMAL = EmbedColor.NORMAL
    INFORMATION = EmbedColor.INFORMATION
    WARNING = EmbedColor.WARNING
    ERROR = EmbedColor.ERROR


async def get_embed(
    type: EmbedType, title: str, description: str, thumbnail_path: Optional[str] = None
) -> Tuple[Embed, Optional[File]]:
    from kusogaki_bot.shared.services.image_service import image_service

    """
    Create a Discord embed with specified type, title, and description.

    Args:
        type (EmbedType): The type of embed which determines its color
        title (str): The embed title
        description (str): The embed description
        thumbnail_path (Optional[str]): Path to thumbnail image. If None, uses default image.

    Returns:
        Tuple[Embed, Optional[File]]: A configured Discord embed and optional file attachment
    """
    embed = Embed(
        title=title,
        description=description,
        color=type.value.value,
        timestamp=datetime.now(),
    )

    if thumbnail_path:
        file = await image_service.get_image_file(thumbnail_path)
        if file:
            embed.set_thumbnail(url=f'attachment://{file.filename}')
    else:
        file = await image_service.get_image_file('static/fern-pout.png')
        if file:
            embed.set_thumbnail(url=f'attachment://{file.filename}')

    return embed, file
