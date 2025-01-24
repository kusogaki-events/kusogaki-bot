import random
from asyncio.log import logger
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import Column, Index, Integer, String, desc, func, select
from sqlalchemy.orm import declarative_base

from kusogaki_bot.core import DatabaseError

Base = declarative_base()


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
    easy_correct: int = 0
    medium_correct: int = 0
    hard_correct: int = 0
    processing_answers: bool = False
    current_round_difficulty: Optional[str] = None


class GTAImage(Base):
    """Database model for anime screenshots"""

    __tablename__ = 'gta_images'

    id = Column(Integer, primary_key=True)
    difficulty = Column(String, nullable=False)
    link = Column(String, nullable=False)
    anime_name = Column(String, nullable=False)


class LeaderboardEntry(Base):
    """Database model for leaderboard entries"""

    __tablename__ = 'gta_game_leaderboard'

    id = Column(Integer, primary_key=True)
    user = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    highest_score = Column(Integer, nullable=False, default=0, index=True)
    place = Column(Integer, nullable=False, index=True)

    __table_args__ = (Index('idx_gta_leaderboard_score_desc', highest_score.desc()),)


class GTARepository:
    """Repository for GTA game data operations"""

    def __init__(self, session_factory) -> None:
        """
        Initialize the GTA repository.

        Args:
            session_factory: SQLAlchemy session factory for database operations.
        """
        self.session_factory = session_factory

    def get_images_batch(
        self, difficulty: str, used_ids: Set[int], batch_size: int = 20
    ) -> List[Tuple[GTAImage, List[str]]]:
        """
        Get a batch of random images and their options efficiently.

        Args:
            difficulty (str): The difficulty level to filter images by.
            used_ids (Set[int]): Set of image IDs that have already been used.
            batch_size (int, optional): Number of images to retrieve. Defaults to 20.

        Returns:
            List[Tuple[GTAImage, List[str]]]: List of tuples containing image objects and their wrong options.

        Raises:
            DatabaseError: If there's an error retrieving images from the database.
        """
        with self.session_factory() as session:
            try:
                stmt = (
                    select(GTAImage)
                    .where(
                        func.lower(GTAImage.difficulty) == difficulty.lower(),
                        ~GTAImage.id.in_(used_ids),
                    )
                    .order_by(func.random())
                    .limit(batch_size)
                )

                images = list(session.execute(stmt).scalars().all())
                if not images:
                    return []

                stmt = select(GTAImage.anime_name).where(
                    func.lower(GTAImage.difficulty) == difficulty.lower()
                )
                all_names = list(session.execute(stmt).scalars().all())

                result = []
                for image in images:
                    wrong_options = [
                        name for name in all_names if name != image.anime_name
                    ]
                    if len(wrong_options) > 10:
                        wrong_options = random.sample(wrong_options, 10)
                    result.append((image, wrong_options))

                return result
            except Exception as e:
                logger.error(f'Failed to get image batch: {str(e)}')
                raise DatabaseError(f'Failed to get image batch: {str(e)}') from e

    def get_random_unused_image(
        self, difficulty: str, used_ids: set[int]
    ) -> Optional[Tuple[GTAImage, List[str]]]:
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
        with self.session_factory() as session:
            try:
                normalized_difficulty = difficulty.lower()
                logger.info(
                    f'Querying database for images with difficulty: {normalized_difficulty}'
                )

                stmt = (
                    select(GTAImage)
                    .where(
                        func.lower(GTAImage.difficulty) == normalized_difficulty,
                        ~GTAImage.id.in_(used_ids),
                    )
                    .order_by(func.random())
                )
                images = session.execute(stmt).scalars().all()

                logger.info(
                    f'Found {len(images)} images for difficulty {normalized_difficulty}'
                )

                if not images:
                    return None

                image = images[0]
                logger.info(
                    f'Selected image link {image.link} with ID {image.id} with difficulty {image.difficulty}'
                )

                stmt = (
                    select(GTAImage.anime_name)
                    .where(
                        GTAImage.anime_name != image.anime_name,
                        func.lower(GTAImage.difficulty) == normalized_difficulty,
                    )
                    .order_by(func.random())
                )
                wrong_options = session.execute(stmt).scalars().all()

                return image, wrong_options
            except Exception as e:
                logger.error(f'Failed to get random unused image: {str(e)}')
                raise DatabaseError(
                    f'Failed to get random unused image: {str(e)}'
                ) from e

    def get_leaderboard(self, limit: int = 5) -> List[LeaderboardEntry]:
        """
        Get top leaderboard entries.

        Args:
            limit (int, optional): Maximum number of entries to retrieve. Defaults to 5.

        Returns:
            List[LeaderboardEntry]: List of top leaderboard entries.

        Raises:
            DatabaseError: If there's an error retrieving leaderboard entries.
        """
        with self.session_factory() as session:
            try:
                stmt = (
                    select(LeaderboardEntry)
                    .order_by(desc(LeaderboardEntry.highest_score))
                    .limit(limit)
                )
                result = session.execute(stmt)
                return list(result.scalars().all())
            except Exception as e:
                logger.error(f'Failed to get leaderboard: {str(e)}')
                raise DatabaseError(f'Failed to get leaderboard: {str(e)}') from e

    def get_player_entry(self, user_id: int) -> Optional[LeaderboardEntry]:
        """
        Get a player's leaderboard entry.

        Args:
            user_id (int): The ID of the player to look up.

        Returns:
            Optional[LeaderboardEntry]: The player's leaderboard entry or None if not found.

        Raises:
            DatabaseError: If there's an error retrieving the player entry.
        """
        with self.session_factory() as session:
            try:
                stmt = select(LeaderboardEntry).where(
                    LeaderboardEntry.user == str(user_id)
                )
                return session.execute(stmt).scalar_one_or_none()
            except Exception as e:
                logger.error(f'Failed to get player entry: {str(e)}')
                raise DatabaseError(f'Failed to get player entry: {str(e)}') from e

    def update_player_score(
        self, user_id: int, display_name: str, score: int
    ) -> Optional[int]:
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
        with self.session_factory() as session:
            try:
                entry = session.execute(
                    select(LeaderboardEntry).where(
                        LeaderboardEntry.user == str(user_id)
                    )
                ).scalar_one_or_none()

                is_new_high_score = False

                if entry:
                    if score > entry.highest_score:
                        entry.highest_score = score
                        entry.display_name = display_name
                        is_new_high_score = True
                else:
                    entry = LeaderboardEntry(
                        user=str(user_id),
                        display_name=display_name,
                        highest_score=score,
                        place=0,
                    )
                    session.add(entry)
                    is_new_high_score = True

                if is_new_high_score:
                    session.commit()
                    self._update_rankings(session)
                    return entry.highest_score
                return None
            except Exception as e:
                session.rollback()
                logger.error(f'Failed to update player score: {str(e)}')
                raise DatabaseError(f'Failed to update player score: {str(e)}') from e

    def _update_rankings(self, session) -> None:
        """
        Update all rankings after a score change.

        Args:
            session: The current database session.

        Raises:
            DatabaseError: If there's an error updating the rankings.
        """
        try:
            entries = (
                session.execute(
                    select(LeaderboardEntry).order_by(
                        desc(LeaderboardEntry.highest_score)
                    )
                )
                .scalars()
                .all()
            )

            for i, e in enumerate(entries, 1):
                e.place = i
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f'Failed to update rankings: {str(e)}')
            raise DatabaseError(f'Failed to update rankings: {str(e)}') from e
