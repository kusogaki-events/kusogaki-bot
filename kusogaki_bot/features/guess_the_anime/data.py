import random
from asyncio.log import logger
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from kusogaki_bot.core import DatabaseError
from kusogaki_bot.core.db import MongoDatabase


class GameDifficulty(Enum):
    """Enum representing different game difficulty levels"""

    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'
    NORMAL = 'normal'

    @classmethod
    def from_str(cls, difficulty: str) -> 'GameDifficulty':
        """
        Convert string to GameDifficulty enum, case-insensitive.

        Args:
            difficulty (str): The difficulty string to convert.

        Returns:
            GameDifficulty: The corresponding GameDifficulty enum value.

        Raises:
            ValueError: If the provided difficulty string is invalid.
        """
        try:
            return cls[difficulty.upper()]
        except KeyError:
            norm_diff = difficulty.lower()
            for diff in cls:
                if diff.value == norm_diff:
                    return diff
            raise ValueError(f'Invalid difficulty: {difficulty}')

    def __str__(self) -> str:
        """Return lowercase difficulty string for database consistency"""
        return self.value.lower()


@dataclass
class PlayerState:
    """Represents a player's state in the current game"""

    id: int
    name: str
    lives: int = 3
    score: int = 0
    pending_high_score: Optional[int] = None


@dataclass
class GameState:
    """Represents the current state of a game session"""

    channel_id: int
    creator_id: int
    players: Dict[int, PlayerState]
    difficulty: GameDifficulty
    is_active: bool = False
    start_time: Optional[datetime] = None
    correct_streak: int = 0
    answered_players: set[int] = field(default_factory=set)
    timed_out_players: set[int] = field(default_factory=set)
    round_feedback: list[str] = field(default_factory=list)
    easy_correct: int = 0
    medium_correct: int = 0
    hard_correct: int = 0
    processing_answers: bool = False
    current_round_difficulty: Optional[str] = None


class GTAImage:
    """GTA Image container"""

    id: int = None
    difficulty: str = None
    link: str = None
    anime_name: str = None


class LeaderboardEntry:
    """Leaderboard Entry Container"""

    id: int = None
    user: str = None
    display_name: str = None
    highest_score: int = None
    place: int = None


class GTARepository:
    """Repository for GTA game data operations"""

    def __init__(self) -> None:
        """
        Initialize the GTA repository.
        """

        self.db = MongoDatabase.get_db()

    async def get_images_batch(self, difficulty: str, used_ids: Set[int], limit: int = 20) -> List[Tuple[GTAImage, List[str]]]:
        """
        Get a batch of random images and their options efficiently.

        Args:
            difficulty (str): The difficulty level to filter images by.
            used_ids (Set[int]): Set of image IDs that have already been used.
            limit (int, optional): Number of images to retrieve. Defaults to 20.

        Returns:
            List[Tuple[GTAImage, List[str]]]: List of tuples containing image objects and their wrong options.

        Raises:
            DatabaseError: If there's an error retrieving images from the database.
        """

        try:
            images_query = {'difficulty': difficulty.capitalize(), 'id': {'$nin': used_ids}}
            names_query = {'difficulty': difficulty.capitalize()}

            images: List[GTAImage] = []
            names: List[str] = []

            image_cursor = self.db['gta-images'].find(images_query, projection={'_id': False}, limit=limit)
            names_cursor = self.db['gta_images'].find(names_query, projection={'anime_name': True, '_id': False})

            async for image in image_cursor:
                gta_image: GTAImage = GTAImage()

                gta_image.id = image.get('id')
                gta_image.anime_name = image.get('anime_name')
                gta_image.difficulty = image.get('difficulty')
                gta_image.link = image.get('link')

                images.append(gta_image)

            async for name in names_cursor:
                names.append(name.get('anime_name'))

            results: List[Tuple[GTAImage, list[str]]] = []

            for image in images:
                incorrect_options = [name for name in names if name != image.anime_name]
                if len(incorrect_options) > 10:
                    incorrect_options = random.sample(incorrect_options, 10)

                results.append((image, incorrect_options))

            return results
        except Exception as e:
            logger.error(f'Failed to get image batch: {str(e)}')
            raise DatabaseError(f'Failed to get image batch: {str(e)}') from e

    async def get_random_unused_image(self, difficulty: str, used_ids: set[int]) -> Optional[Tuple[GTAImage, List[str]]]:
        """
        Get random unused image and wrong options strictly matching the difficulty.

        Args:
            difficulty (str): The difficulty level to filter images by.
            used_ids (set[int]): Set of image IDs that have already been used.

        Returns:
            Optional[Tuple[GTAImage, List[str]]]: Tuple containing the image and wrong options,
                                                or None if no unused images are found.

        Raises:
            DatabaseError: If there's an error retrieving the image from the database.
        """

        try:
            images_query = {'difficulty': difficulty.capitalize(), 'id': {'$nin': used_ids}}
            names_query = {'difficulty': difficulty.capitalize()}

            names: List[str] = []

            image_cursor = await self.db['gta-images'].find_one(images_query, projection={'_id': False})
            names_cursor = self.db['gta_images'].find(names_query, projection={'anime_name': True, '_id': False})

            gta_image: GTAImage = GTAImage()

            gta_image.id = image_cursor.get('id')
            gta_image.anime_name = image_cursor.get('anime_name')
            gta_image.difficulty = image_cursor.get('difficulty')
            gta_image.link = image_cursor.get('link')

            async for name in names_cursor:
                if name == gta_image.anime_name:
                    continue
                names.append(name.get('anime_name'))

            incorrect_options = random.sample(names, 10)

            return (gta_image, incorrect_options)

        except Exception as e:
            logger.error(f'Failed to get random unused image: {str(e)}')
            raise DatabaseError(f'Failed to get random unused image: {str(e)}') from e

    async def get_leaderboard(self, limit: int = 5) -> List[LeaderboardEntry]:
        """
        Get top leaderboard entries.

        Args:
            limit (int, optional): Maximum number of entries to retrieve. Defaults to 5.

        Returns:
            List[LeaderboardEntry]: List of top leaderboard entries.

        Raises:
            DatabaseError: If there's an error retrieving leaderboard entries.
        """

        try:
            leaderboard_cursor = self.db['gta_game_leaderboard'].find({}, limit=limit).sort({'highest_score': -1})

            results: List[LeaderboardEntry] = []

            async for leaderboard_entry in leaderboard_cursor:
                entry: LeaderboardEntry = LeaderboardEntry()

                entry.id = leaderboard_entry.get('id')
                entry.user = leaderboard_entry.get('user')
                entry.highest_score = leaderboard_entry.get('highest_score')
                entry.place = leaderboard_entry.get('place')
                entry.display_name = leaderboard_entry.get('display_name')

                results.append(entry)

            return results

        except Exception as e:
            logger.error(f'Failed to get leaderboard: {str(e)}')
            raise DatabaseError(f'Failed to get leaderboard: {str(e)}') from e

    async def get_player_entry(self, user_id: int) -> Optional[LeaderboardEntry]:
        """
        Get a player's leaderboard entry.

        Args:
            user_id (int): The ID of the player to look up.

        Returns:
            Optional[LeaderboardEntry]: The player's leaderboard entry or None if not found.

        Raises:
            DatabaseError: If there's an error retrieving the player entry.
        """

        try:
            query = {'user': str(user_id)}

            leaderboard_cursor = await self.db['gta_game_leaderboard'].find_one(query)

            entry: LeaderboardEntry = LeaderboardEntry()

            entry.id = leaderboard_cursor.get('id')
            entry.user = leaderboard_cursor.get('user')
            entry.highest_score = leaderboard_cursor.get('highest_score')
            entry.place = leaderboard_cursor.get('place')
            entry.display_name = leaderboard_cursor.get('display_name')

            return entry

        except Exception as e:
            logger.error(f'Failed to get player entry: {str(e)}')
            raise DatabaseError(f'Failed to get player entry: {str(e)}') from e

    async def update_player_score(self, user_id: int, display_name: str, score: int) -> Optional[int]:
        """
        Update a player's score.

        Args:
            user_id (int): The ID of the player to update.
            display_name (str): The display name of the player.
            score (int): The new score to record.

        Returns:
            Optional[int]: The player's new highest score if updated, None otherwise.

        Raises:
            DatabaseError: If there's an error updating the player's score.
        """

        try:
            query = {'user': str(user_id)}

            user_details = await self.db['gta_game_leaderboard'].find_one(query)

            if user_details:
                if user_details.get('highest_score') < score:
                    updates = {'display_name': display_name, 'highest_score': score}
                    await self.db['gta_game_leaderboard'].update_one(query, update={'$set': updates})
                    await self._update_rankings()
                else:
                    return user_details.get('highest_score')

            else:
                user_details = {'user': user_id, 'display_name': display_name, 'highest_score': score, 'place': 0, 'id': 0}
                await self.db['gta_game_leaderboard'].insert_one(user_details)

            return score

        except Exception as e:
            logger.error(f'Failed to update player score: {str(e)}')
            raise DatabaseError(f'Failed to update player score: {str(e)}') from e

    async def _update_rankings(self) -> None:
        """
        Update all rankings after a score change.

        Args:
            session: The current database session.

        Raises:
            DatabaseError: If there's an error updating the rankings.
        """
        try:
            entries = entries = self.db['gta_game_leaderboard'].find({}).sort({'highest_score': -1})

            place = 1
            async for entry in entries:
                await self.db['gta_game_leaderboard'].update_one({'user': entry.get('user')}, update={'$set': {'place': place}})
                place = place + 1

        except Exception as e:
            logger.error(f'Failed to update rankings: {str(e)}')
            raise DatabaseError(f'Failed to update rankings: {str(e)}') from e
