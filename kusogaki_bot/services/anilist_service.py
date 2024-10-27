import asyncio
import logging
import random
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class AniListService:
    """Service for handling AniList API requests."""

    def __init__(self):
        self.base_url = 'https://graphql.anilist.co'
        self.session: Optional[aiohttp.ClientSession] = None
        self.MAX_PAGE = 500
        self.cached_anime: List[Dict[str, Any]] = []
        self.last_cache_update = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _fetch_anime_batch(
        self, page: int = 1, per_page: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch a batch of anime from AniList."""
        query = """
        query ($page: Int, $perPage: Int) {
            Page(page: $page, perPage: $perPage) {
                pageInfo {
                    total
                    currentPage
                    lastPage
                    hasNextPage
                }
                media(type: ANIME, format: TV, sort: POPULARITY_DESC, status: FINISHED) {
                    id
                    title {
                        romaji
                        english
                    }
                    coverImage {
                        large
                    }
                    popularity
                    averageScore
                }
            }
        }
        """

        variables = {'page': page, 'perPage': per_page}

        try:
            data = await self._make_request(query, variables)
            if data and 'Page' in data and 'media' in data['Page']:
                return [
                    m
                    for m in data['Page']['media']
                    if m.get('coverImage')
                    and m['coverImage'].get('large')
                    and (m['title'].get('english') or m['title'].get('romaji'))
                ]
            return []
        except Exception as e:
            logger.error(f'Error fetching anime batch: {e}', exc_info=True)
            return []

    async def _update_cache(self) -> None:
        """Update the anime cache with fresh data."""
        try:
            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_cache_update < 3600:
                return

            tasks = [self._fetch_anime_batch(page) for page in range(1, 4)]
            results = await asyncio.gather(*tasks)

            new_cache = []
            for batch in results:
                new_cache.extend(batch)

            if new_cache:
                self.cached_anime = new_cache
                self.last_cache_update = current_time
                logger.info(
                    f'Updated anime cache with {len(self.cached_anime)} entries'
                )
            else:
                logger.warning('Failed to update cache - no valid anime found')

        except Exception as e:
            logger.error(f'Error updating cache: {e}', exc_info=True)

    async def get_random_anime(self, max_retries: int = 3) -> Dict[str, Any]:
        """Get a random anime entry."""
        try:
            await self._update_cache()

            if not self.cached_anime:
                anime_list = await self._fetch_anime_batch(
                    page=random.randint(1, self.MAX_PAGE)
                )
                if not anime_list:
                    raise Exception('Could not fetch any anime')
                return random.choice(anime_list)

            return random.choice(self.cached_anime)

        except Exception as e:
            logger.error(f'Error getting random anime: {e}', exc_info=True)
            raise Exception('Could not find a valid anime after multiple attempts')

    async def _make_request(
        self, query: str, variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make GraphQL request to AniList API."""
        for attempt in range(3):
            try:
                session = await self._get_session()
                async with session.post(
                    self.base_url,
                    json={'query': query, 'variables': variables},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 429:
                        await asyncio.sleep(60)
                        continue

                    data = await response.json()
                    if 'errors' in data:
                        logger.warning(f"AniList API error: {data['errors']}")
                        continue

                    return data['data']

            except asyncio.TimeoutError:
                logger.warning(f'Request timeout on attempt {attempt + 1}')
                await asyncio.sleep(1)
            except aiohttp.ClientError as e:
                logger.error(f'Network error in AniList API request: {e}')
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f'Unexpected error in API request: {e}')
                await asyncio.sleep(1)

        raise Exception('Failed to connect to AniList after multiple attempts')