import asyncio
import random
from asyncio.log import logger
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from discord import File

from kusogaki_bot.features.guess_the_anime.data import (
    GameDifficulty,
    GameState,
    GTARepository,
    LeaderboardEntry,
    PlayerState,
)
from kusogaki_bot.shared import ImagePreloader, ImageUrlHandler
from kusogaki_bot.shared.services import image_service


def ensure_direct_image_url(url: str) -> str:
    """
    Convert various image hosting URLs to direct image URLs.

    Args:
        url: The URL to convert to a direct image URL.

    Returns:
        str: The converted direct image URL.
    """
    return ImageUrlHandler.transform_url(url)


@dataclass
class CommandResult:
    success: bool
    message: str


class GTAGameService:
    """Service for handling Guess The Anime game logic"""

    def __init__(self, repository: GTARepository) -> None:
        """
        Initialize the Guess The Anime game service.

        Args:
            repository: Repository instance for data persistence.
        """
        self.repository = repository
        self.games: Dict[int, GameState] = {}
        self.used_image_ids: Dict[int, set[int]] = {}
        self.LOADING_TIME = 15
        self.ROUND_TIME = 10
        self.MAX_OPTIONS = 4
        self.EASY_THRESHOLD = 2
        self.MEDIUM_THRESHOLD = 2
        self.HARD_THRESHOLD = 3

        self.image_preloader = ImagePreloader(repository)
        difficulties = [diff.value for diff in GameDifficulty]
        asyncio.create_task(self.image_preloader.initialize(difficulties))

    def create_game(
        self, channel_id: int, creator_id: int, difficulty: str, creator_name: str
    ) -> CommandResult:
        """
        Create a new game with specified difficulty.

        Args:
            channel_id: Discord channel ID where the game is being created.
            creator_id: Discord user ID of the game creator.
            difficulty: Difficulty level for the game (easy, medium, hard, or normal).
            creator_name: Display name of the game creator.

        Returns:
            CommandResult: Result object containing success status and message.
        """
        if channel_id in self.games:
            return CommandResult(False, 'A game is already running in this channel!')

        if not difficulty:
            game_difficulty = GameDifficulty.NORMAL
        else:
            try:
                game_difficulty = GameDifficulty.from_str(difficulty)
            except ValueError:
                return CommandResult(
                    False,
                    'Invalid difficulty! Choose from: easy, medium, hard, or normal',
                )

        self.games[channel_id] = GameState(
            channel_id=channel_id,
            creator_id=creator_id,
            players={},
            difficulty=game_difficulty,
            easy_correct=0,
            medium_correct=0,
            hard_correct=0,
            correct_streak=0,
        )
        self.used_image_ids[channel_id] = set()

        self.add_player(channel_id, creator_id, creator_name)
        return CommandResult(
            True, f'Game created with {str(game_difficulty).title()} difficulty'
        )

    def start_game(self, channel_id: int) -> bool:
        """
        Mark a game as started.

        Args:
            channel_id: Discord channel ID of the game.

        Returns:
            bool: True if game successfully started, False otherwise.
        """
        game = self.games.get(channel_id)
        if not game or not game.players:
            return False

        game.is_active = True
        game.start_time = datetime.now()
        return True

    def start_next_round(self, channel_id: int) -> None:
        """
        Reset game state for next round.

        Args:
            channel_id: Discord channel ID of the game.
        """
        game = self.games.get(channel_id)
        if game:
            game.answered_players.clear()
            game.timed_out_players.clear()
            game.processing_answers = False

    def stop_game(self, channel_id: int, user_id: int) -> CommandResult:
        """
        Stop an active game.

        Args:
            channel_id: Discord channel ID of the game.
            user_id: Discord user ID of the user attempting to stop the game.

        Returns:
            CommandResult: Result object containing success status and message.
        """
        game = self.games.get(channel_id)
        if not game:
            return CommandResult(False, 'No active game to stop!')

        if game.creator_id != user_id:
            return CommandResult(False, 'Only the game creator can stop the game!')

        self.cleanup_game(channel_id)
        return CommandResult(True, 'Game stopped!')

    def cleanup_game(self, channel_id: int) -> None:
        """
        Clean up game resources for a channel.

        Args:
            channel_id: Discord channel ID of the game to clean up.
        """
        if channel_id in self.games:
            del self.games[channel_id]
        if channel_id in self.used_image_ids:
            del self.used_image_ids[channel_id]

    def add_player(
        self, channel_id: int, player_id: int, player_name: str
    ) -> CommandResult:
        """
        Add a player to an existing game.

        Args:
            channel_id: Discord channel ID of the game.
            player_id: Discord user ID of the player to add.
            player_name: Display name of the player.

        Returns:
            CommandResult: Result object containing success status and message.
        """
        game = self.games.get(channel_id)
        if not game:
            return CommandResult(False, 'No game available to join!')

        if game.is_active:
            return CommandResult(False, 'Cannot join an active game!')

        if player_id in game.players:
            return CommandResult(False, 'You are already in the game!')

        game.players[player_id] = PlayerState(id=player_id, name=player_name)
        return CommandResult(True, f'{player_name} joined the game!')

    def get_active_players(self, channel_id: int) -> List[PlayerState]:
        """
        Get list of active players in a game.

        Args:
            channel_id: Discord channel ID of the game.

        Returns:
            List[PlayerState]: List of active player states (players with lives > 0).
        """
        game = self.games.get(channel_id)
        if not game:
            return []
        return [p for p in game.players.values() if p.lives > 0]

    def get_game(self, channel_id: int) -> Optional[GameState]:
        """
        Get game state for a channel.

        Args:
            channel_id: Discord channel ID.

        Returns:
            Optional[GameState]: Game state if it exists

        Raises:
            GameNotFoundError: If no game exists for the channel
        """
        return self.games.get(channel_id)

    def check_game_over(self, channel_id: int) -> Tuple[bool, Optional[Dict[int, int]]]:
        """
        Check if the game should end and get final scores.

        Args:
            channel_id: Discord channel ID of the game.

        Returns:
            Tuple containing:
                - bool: Whether the game is over
                - Optional[Dict[int, int]]: Dictionary mapping player IDs to final scores, None if game not over
        """
        game = self.games.get(channel_id)
        if not game:
            return True, None

        active_players = [p for p in game.players.values() if p.lives > 0]
        if not active_players:
            final_scores = {p.id: p.score for p in game.players.values()}
            return True, final_scores

        return False, None

    def get_current_difficulty(self, game: GameState) -> str:
        """
        Get current difficulty based on game mode and progress.

        Args:
            game: Current game state object.

        Returns:
            str: Current difficulty level as a string.
        """
        if game.difficulty != GameDifficulty.NORMAL:
            return str(game.difficulty)

        if game.easy_correct < self.EASY_THRESHOLD:
            return str(GameDifficulty.EASY)
        elif game.medium_correct < self.MEDIUM_THRESHOLD:
            return str(GameDifficulty.MEDIUM)
        elif game.hard_correct < self.HARD_THRESHOLD:
            return str(GameDifficulty.HARD)
        else:
            return str(
                random.choice(
                    [GameDifficulty.EASY, GameDifficulty.MEDIUM, GameDifficulty.HARD]
                )
            )

    async def get_round_data(
        self, channel_id: int
    ) -> Tuple[Optional[File], List[str], str]:
        """
        Get data for the next round with improved error handling.

        Args:
            channel_id: Discord channel ID of the game.

        Returns:
            Tuple containing:
                - Optional[File]: Discord File object containing the image, None if error
                - List[str]: List of possible answers
                - str: Correct answer

        Raises:
            ValueError: If no game exists or round data cannot be prepared
        """
        game = self.games.get(channel_id)
        if not game:
            raise ValueError('No active game')

        game.current_round_difficulty = self.get_current_difficulty(game)
        logger.info(
            f'Current game state - Easy: {game.easy_correct}/{self.EASY_THRESHOLD}, '
            f'Medium: {game.medium_correct}/{self.MEDIUM_THRESHOLD}, '
            f'Hard: {game.hard_correct}/{self.HARD_THRESHOLD}'
        )
        logger.info(
            f'Looking for image with difficulty: {game.current_round_difficulty}'
        )

        try:
            image_data = await self.image_preloader.get_next_image(
                game.current_round_difficulty
            )
            if not image_data:
                logger.warning(
                    f'No preloaded images for {game.current_round_difficulty}'
                )
                await self.image_preloader.cleanup_category(
                    game.current_round_difficulty
                )
                image_data = await self.image_preloader.get_next_image(
                    game.current_round_difficulty
                )
                if not image_data:
                    raise ValueError(
                        f'No images available for difficulty {game.current_round_difficulty}'
                    )

            image, wrong_options = image_data

            image_file = await image_service.get_image_file(image.link)
            if not image_file:
                logger.error(f'Failed to load image from {image.link}')
                return None, [], ''

            options = random.sample(
                wrong_options, min(self.MAX_OPTIONS - 1, len(wrong_options))
            )
            options.append(image.anime_name)
            random.shuffle(options)

            return image_file, options, image.anime_name

        except Exception as e:
            logger.error(f'Error getting round data: {e}', exc_info=True)
            raise ValueError('Failed to prepare round data')

    def process_answer(
        self, channel_id: int, player_id: int, answer: str, correct_answer: str
    ) -> Tuple[bool, bool, Optional[int]]:
        """
        Process a player's answer with improved timeout handling.

        Args:
            channel_id: Discord channel ID of the game.
            player_id: Discord user ID of the player answering.
            answer: The player's submitted answer.
            correct_answer: The correct answer for comparison.

        Returns:
            Tuple containing:
                - bool: Whether the answer was correct
                - bool: Whether the player is eliminated
                - Optional[int]: New high score if achieved, None otherwise
        """
        game = self.games.get(channel_id)
        if not game:
            return False, False, None

        try:
            player = game.players[player_id]
            is_correct = answer == correct_answer

            if player_id in game.timed_out_players:
                logger.warning(f'Player {player_id} attempted to answer after timeout')
                return False, player.lives <= 0, None

            if is_correct:
                current_diff = self.get_current_difficulty(game)
                logger.info(
                    f'Processing correct answer - Current difficulty: {current_diff}'
                )

                if current_diff == str(GameDifficulty.EASY):
                    game.easy_correct += 1
                    player.score += 1
                    logger.info(
                        f'Got EASY correct. Totals - Easy: {game.easy_correct}, Medium: {game.medium_correct}, Hard: {game.hard_correct}'
                    )
                elif current_diff == str(GameDifficulty.MEDIUM):
                    game.medium_correct += 1
                    player.score += 2
                    logger.info(
                        f'Got MEDIUM correct. Totals - Easy: {game.easy_correct}, Medium: {game.medium_correct}, Hard: {game.hard_correct}'
                    )
                elif current_diff == str(GameDifficulty.HARD):
                    game.hard_correct += 1
                    player.score += 3
                    logger.info(
                        f'Got HARD correct. Totals - Easy: {game.easy_correct}, Medium: {game.medium_correct}, Hard: {game.hard_correct}'
                    )

                new_high_score = self.repository.update_player_score(
                    player_id, player.name, player.score
                )
                return True, False, new_high_score
            else:
                if player_id not in game.timed_out_players:
                    player.lives -= 1
                    game.correct_streak = 0
                return False, player.lives <= 0, None

        except Exception as e:
            logger.error(f'Error processing answer: {e}', exc_info=True)
            if game and player_id in game.answered_players:
                game.answered_players.remove(player_id)
            raise

    def handle_game_timeout(self, channel_id: int) -> List[Tuple[str, int]]:
        """
        Handle timeout for a game channel with race condition protection.

        Args:
            channel_id: Discord channel ID of the game.

        Returns:
            List[Tuple[str, int]]: List of tuples containing (player_name, remaining_lives) for timed out players.
        """
        game = self.games.get(channel_id)
        if not game:
            return []

        timed_out_players = []
        for player in game.players.values():
            if (
                player.lives > 0
                and player.id not in game.answered_players
                and player.id not in game.timed_out_players
            ):
                player.lives -= 1
                game.correct_streak = 0
                game.timed_out_players.add(player.id)
                timed_out_players.append((player.name, player.lives))

        return timed_out_players

    def have_all_players_answered(self, channel_id: int) -> bool:
        """
        Check if all active players have submitted an answer.

        Args:
            channel_id: Discord channel ID of the game.

        Returns:
            bool: True if all active players have answered, False otherwise.
        """
        game = self.games.get(channel_id)
        if not game:
            return False

        active_players = set(p.id for p in game.players.values() if p.lives > 0)
        return active_players.issubset(game.answered_players)

    def get_leaderboard(self) -> List[LeaderboardEntry]:
        """
        Get global leaderboard entries.

        Returns:
            List[LeaderboardEntry]: List of leaderboard entries sorted by score.
        """
        return self.repository.get_leaderboard()

    def get_player_stats(self, user_id: int) -> Optional[LeaderboardEntry]:
        """
        Get stats for a specific player.

        Args:
            user_id: Discord user ID of the player.

        Returns:
            Optional[LeaderboardEntry]: Player's leaderboard entry if it exists, None otherwise.
        """
        return self.repository.get_player_entry(user_id)
