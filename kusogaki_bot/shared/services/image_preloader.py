import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

from kusogaki_bot.shared.services.image_service import image_service
from kusogaki_bot.shared.utils.images import ImageUrlHandler

logger = logging.getLogger(__name__)


class ImageProvider(Protocol):
    """Protocol for providing images to preload"""

    def get_random_unused_image(
        self, category: str, used_ids: Set[int]
    ) -> Optional[Tuple[Any, List[str]]]:
        """
        Get random unused image for a category.

        Args:
            category (str): The category to get an image from
            used_ids (Set[int]): Set of already used image IDs to avoid duplicates

        Returns:
            Optional[Tuple[Any, List[str]]]: Tuple containing the image object and a list of options,
                                           or None if no unused images are available
        """
        ...


class ImagePreloader:
    """
    Enhanced batch image preloader with aggressive caching.

    Handles preloading and caching of images for different categories with parallel processing
    and efficient batch operations.

    Attributes:
        provider (ImageProvider): The image provider implementation
        preload_count (int): Number of images to preload per category
        preloaded_images (Dict[str, List[dict]]): Cache of preloaded images per category
        used_images (Dict[str, Set[int]]): Tracking of used image IDs per category
        _preload_lock (asyncio.Lock): Lock for synchronizing preload operations
        _preload_tasks (Dict[str, asyncio.Task]): Active preload tasks per category
        _batch_size (int): Size of batches for preloading operations
    """

    def __init__(self, provider: ImageProvider, preload_count: int = 20) -> None:
        """
        Initialize the ImagePreloader.

        Args:
            provider (ImageProvider): The image provider implementation
            preload_count (int, optional): Number of images to preload per category. Defaults to 20.
        """
        self.provider = provider
        self.preload_count = preload_count
        self.preloaded_images: Dict[str, List[dict]] = defaultdict(list)
        self.used_images: Dict[str, Set[int]] = defaultdict(set)
        self._preload_lock = asyncio.Lock()
        self._preload_tasks: Dict[str, asyncio.Task] = {}
        self._batch_size = max(5, preload_count // 2)

    async def initialize(self, categories: List[str]) -> None:
        """
        Initialize with parallel preloading for each category.

        Args:
            categories (List[str]): List of categories to initialize preloading for
        """
        await asyncio.gather(
            *[self._preload_batch(category) for category in categories]
        )

    async def _preload_batch(self, category: str) -> None:
        """
        Preload a batch of images with improved error handling.

        Args:
            category (str): Category to preload images for

        Note:
            This method handles both batch and individual image loading depending on
            provider capabilities. It transforms URLs and updates the internal cache
            while maintaining the preload count limit.
        """
        try:
            if len(self.preloaded_images[category]) >= self.preload_count:
                return

            if hasattr(self.provider, 'get_images_batch'):
                images_data = await self.provider.get_images_batch(
                    category, self.used_images[category], self._batch_size
                )
            else:
                images_data = []
                while len(images_data) < self._batch_size:
                    image_data = self.provider.get_random_unused_image(
                        category, self.used_images[category]
                    )
                    if not image_data:
                        break
                    images_data.append(image_data)

            image_urls = []
            for image, _ in images_data:
                image_source = ImageUrlHandler.process_url(image.link)
                image_urls.append(image_source.url)
                image.link = image_source.url

            await image_service.preload_images(image_urls)

            for image, options in images_data:
                if len(self.preloaded_images[category]) >= self.preload_count:
                    break

                self.used_images[category].add(image.id)
                self.preloaded_images[category].append(
                    {'image': image, 'options': options}
                )

        except Exception as e:
            logger.error(f'Error preloading images for {category}: {e}')
        finally:
            if category in self._preload_tasks:
                del self._preload_tasks[category]

    async def get_next_image(self, category: str) -> Optional[tuple]:
        """
        Get next image and trigger background preload if needed.

        Args:
            category (str): Category to get the next image from

        Returns:
            Optional[Tuple[Any, List[str]]]: Tuple containing the image object and a list of options,
                                           or None if no images are available

        Note:
            This method automatically triggers a background preload task when the cache
            gets below half capacity for the specified category.
        """
        if not self.preloaded_images[category]:
            await self._preload_batch(category)
            if not self.preloaded_images[category]:
                return None

        image_data = self.preloaded_images[category].pop(0)

        if (
            len(self.preloaded_images[category]) < self.preload_count / 2
            and category not in self._preload_tasks
        ):
            self._preload_tasks[category] = asyncio.create_task(
                self._preload_batch(category)
            )

        return image_data['image'], image_data['options']

    async def cleanup_category(self, category: str):
        """
        Reset category state and trigger fresh preload.

        Args:
            category (str): Category to reset and reload

        Note:
            This method cancels any active preload tasks for the category,
            clears all cached data, and initiates a fresh preload operation.
        """
        self.used_images[category].clear()
        self.preloaded_images[category].clear()
        if category in self._preload_tasks:
            self._preload_tasks[category].cancel()
            del self._preload_tasks[category]
        await self._preload_batch(category)
