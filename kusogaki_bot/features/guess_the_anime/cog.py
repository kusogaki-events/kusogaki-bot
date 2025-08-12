import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from kusogaki_bot.core import BaseCog, KusogakiBot
from kusogaki_bot.features.guess_the_anime.data import GTARepository
from kusogaki_bot.features.guess_the_anime.service import GTAGameService
from kusogaki_bot.shared import EmbedColor, EmbedType

logger = logging.getLogger(__name__)


class AnswerView(discord.ui.View):
    """
    A Discord UI View for handling answer buttons in the Guess The Anime quiz game.

    Attributes:
        cog (GTAQuizCog): The cog instance that owns this view
        correct_answer (str): The correct answer for the current question
        processing_lock (asyncio.Lock): Lock to prevent concurrent answer processing
    """

    def __init__(self, cog: 'GTAQuizCog', options: List[str], correct_answer: str) -> None:
        """
        Initialize the answer view with buttons for each option.

        Args:
            cog (GTAQuizCog): The cog instance that owns this view
            options (List[str]): List of possible answers to display as buttons
            correct_answer (str): The correct answer for the current question
        """
        super().__init__(timeout=None)
        self.cog = cog
        self.correct_answer = correct_answer
        self.processing_lock = asyncio.Lock()

        for i, option in enumerate(options):
            button = discord.ui.Button(
                label=str(i + 1),
                style=discord.ButtonStyle.primary,
                custom_id=f'answer_{i}',
                row=0,
            )
            button.callback = self.make_callback(option)
            self.add_item(button)

    def make_callback(self, answer: str) -> Callable[[discord.Interaction], Awaitable[None]]:
        """
        Create a callback function for an answer button.

        Args:
            answer (str): The answer associated with this button

        Returns:
            Callable: Async callback function that handles button interactions
        """

        async def button_callback(interaction: discord.Interaction):
            try:
                game_state = self.cog.service.get_game(interaction.channel.id)
                if not game_state:
                    await interaction.response.send_message('No active game found!', ephemeral=True)
                    return

                async with self.processing_lock:
                    if interaction.user.id in game_state.answered_players:
                        await interaction.response.send_message('You already answered!', ephemeral=True)
                        return

                    game_state.answered_players.add(interaction.user.id)

                    await self.cog._handle_answer(interaction, answer, self.correct_answer)
                    await interaction.response.defer()

            except Exception as e:
                logger.error(f'Error in button callback: {e}', exc_info=True)
                if game_state:
                    try:
                        game_state.answered_players.remove(interaction.user.id)
                    except KeyError:
                        pass
                try:
                    await interaction.response.send_message(
                        'Something went wrong processing your answer. Please try again.',
                        ephemeral=True,
                    )
                except discord.errors.InteractionResponded:
                    await interaction.followup.send(
                        'Something went wrong processing your answer. Please try again.',
                        ephemeral=True,
                    )

        return button_callback


class JoinView(discord.ui.View):
    """
    A Discord UI View for handling the join button in the Guess The Anime quiz game.

    Attributes:
        cog (GTAQuizCog): The cog instance that owns this view
    """

    def __init__(self, cog: 'GTAQuizCog') -> None:
        """
        Initialize the view with a join button.

        Args:
            cog (GTAQuizCog): The cog instance that owns this view
        """
        super().__init__(timeout=None)
        self.cog = cog

        button = discord.ui.Button(
            label='Join',
            style=discord.ButtonStyle.primary,
            custom_id='join',
            row=0,
        )
        button.callback = self.make_callback()
        self.add_item(button)

    def make_callback(
        self,
    ) -> Callable[[discord.Interaction], Awaitable[None]]:
        """
        Create a callback function for the join button.

        Returns:
            Callable: Async callback function that handles button interactions
        """

        async def button_callback(interaction: discord.Interaction):
            try:
                game_state = self.cog.service.get_game(interaction.channel.id)
                if not game_state:
                    await interaction.response.send_message('No active game found!', ephemeral=True)
                    return

                await self.cog.join_game(interaction=interaction)

            except Exception as e:
                logger.error(f'Error in button callback: {e}', exc_info=True)

                try:
                    await interaction.response.send_message(
                        'Something went wrong joining the game. Please try again.',
                        ephemeral=True,
                    )
                except discord.errors.InteractionResponded:
                    await interaction.followup.send(
                        'Something went wrong joining the game. Please try again.',
                        ephemeral=True,
                    )

        return button_callback


class GTAQuizCog(BaseCog):
    """
    Cog for the Guess The Anime quiz game. Handles all game-related commands and interactions.

    This cog implements a multiplayer quiz game where players try to guess anime titles
    from screenshots or images. It includes features like difficulty settings, scoring,
    lives system, and a leaderboard.

    Attributes:
        service (GTAGameService): Service layer handling game logic
        active_countdowns (Dict[int, asyncio.Task]): Active countdown tasks by channel ID
    """

    def __init__(self, bot: KusogakiBot) -> None:
        """
        Initialize the GTAQuizCog.

        Args:
            bot (KusogakiBot): The bot instance this cog is attached to
        """
        super().__init__(bot)
        repository = GTARepository()
        self.service = GTAGameService(repository)
        self.active_countdowns: Dict[int, asyncio.Task] = {}

    async def cog_unload(self) -> None:
        """
        Clean up resources when the cog is unloaded.

        Cancels all active countdown tasks to ensure proper cleanup.
        This method is called automatically by Discord.py when the cog is unloaded.
        """
        for task in self.active_countdowns.values():
            task.cancel()
        self.active_countdowns.clear()

    @commands.hybrid_group(name='gtaquiz', aliases=['gq'])
    async def gta_quiz(self, ctx: commands.Context) -> None:
        """
        Main command group for the Guess The Anime quiz game.

        If no subcommand is provided, displays the list of available commands.

        Args:
            ctx (commands.Context): The command context
        """
        if ctx.invoked_subcommand is None:
            await ctx.send('Available commands: `start`, `stop`, `leaderboard`, `score`')

    @gta_quiz.command(name='start')
    @app_commands.describe(difficulty='Game difficulty (easy, medium, hard, normal)')
    async def start_game(self, ctx: commands.Context, difficulty: str = 'normal') -> None:
        """
        Start a new Guess The Anime quiz game in the current channel.

        Initiates a countdown timer and waits for players to join before starting the game.
        Only one game can be active per channel.

        Args:
            ctx (commands.Context): The command context
            difficulty (str, optional): Game difficulty level. Defaults to 'normal'

        Raises:
            Exception: If there's an error during game creation or countdown initialization
        """
        try:
            if ctx.channel.id in self.active_countdowns:
                await ctx.send('A game is already starting in this channel!')
                return

            result = self.service.create_game(ctx.channel.id, ctx.author.id, difficulty, ctx.author.name)
            if not result.success:
                await ctx.send(result.message)
                return

            view = JoinView(self)

            player_names = (f'<@{player_id}>' for player_id in self.service.get_game(ctx.channel.id).players.keys())

            embed, file = await self.create_embed(
                EmbedType.NORMAL,
                '🎮 Guess The Anime Quiz',
                f'{result.message}\nPlayer(s): {", ".join(player_names)}\n\nPress the button to join!',
            )

            msg = await ctx.send(embed=embed, file=file, view=view)

            logger.info(f'Starting countdown for channel {ctx.channel.id}')
            task = asyncio.create_task(self._run_countdown(ctx.channel.id, msg))
            self.active_countdowns[ctx.channel.id] = task

            def countdown_done(task) -> None:
                try:
                    task.result()
                except Exception as e:
                    logger.error(f'Countdown task failed: {e}', exc_info=True)
                    asyncio.create_task(ctx.send('An error occurred during game startup.'))
                finally:
                    if ctx.channel.id in self.active_countdowns:
                        del self.active_countdowns[ctx.channel.id]

            task.add_done_callback(countdown_done)

        except Exception as e:
            logger.error(f'Error starting game: {e}', exc_info=True)
            await ctx.send('An error occurred while starting the game.')
            if ctx.channel.id in self.active_countdowns:
                self.active_countdowns[ctx.channel.id].cancel()
                del self.active_countdowns[ctx.channel.id]

    async def join_game(self, interaction: discord.Interaction) -> None:
        """
        Join an ongoing game in the current channel.

        Players can only join during the countdown phase before the game starts.

        Args:
            interaction (discord.Interaction): The button interaction triggering the join

        Raises:
            Exception: If there's an error adding the player to the game
        """
        try:
            result = self.service.add_player(interaction.channel.id, interaction.user.id, interaction.user.name)
            if result.success:
                await interaction.response.send_message(result.message)
            else:
                await interaction.response.send_message(result.message, ephemeral=True)

        except Exception as e:
            logger.error(f'Error joining game: {e}')
            await interaction.response.send_message('An error occurred while joining the game.', ephemeral=True)

    @gta_quiz.command(name='stop')
    async def stop_game(self, ctx: commands.Context) -> None:
        """
        Stop the current game in the channel.

        Only the game creator or server administrators can stop the game.

        Args:
            ctx (commands.Context): The command context

        Raises:
            Exception: If there's an error stopping the game
        """
        try:
            result = self.service.stop_game(ctx.channel.id, ctx.author.id)
            if result.success and ctx.channel.id in self.active_countdowns:
                self.active_countdowns[ctx.channel.id].cancel()
                del self.active_countdowns[ctx.channel.id]
            await ctx.send(result.message)
        except Exception as e:
            logger.error(f'Error stopping game: {e}')
            await ctx.send('An error occurred while stopping the game.')

    @gta_quiz.command(name='leaderboard')
    async def show_leaderboard(self, ctx: commands.Context) -> None:
        """
        Display the global leaderboard showing top players and their scores.

        Shows a ranked list of players with their highest achieved scores.
        Top 3 players are highlighted with special medals.

        Args:
            ctx (commands.Context): The command context

        Raises:
            Exception: If there's an error fetching or displaying the leaderboard
        """
        try:
            entries = self.service.get_leaderboard()

            if not entries:
                embed, file = await self.create_embed(EmbedType.NORMAL, '🏆 Leaderboard', 'No scores yet!')
            else:
                description = []
                for i, entry in enumerate(entries, 1):
                    medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, '🎮')
                    description.append(f'{medal} #{i} - {entry.display_name}: {entry.highest_score} points')

                embed, file = await self.create_embed(
                    EmbedType.NORMAL,
                    '🏆 Guess The Anime Leaderboard',
                    '\n'.join(description),
                )

            await ctx.send(embed=embed, file=file)

        except Exception as e:
            logger.error(f'Error showing leaderboard: {e}')
            await ctx.send('An error occurred while fetching the leaderboard.')

    @gta_quiz.command(name='score')
    async def show_score(self, ctx: commands.Context) -> None:
        """
        Display the requesting player's personal stats.

        Shows the player's current rank and highest achieved score.

        Args:
            ctx (commands.Context): The command context

        Raises:
            Exception: If there's an error fetching or displaying the player's stats
        """
        try:
            entry = self.service.get_player_stats(ctx.author.id)

            if not entry:
                description = "You haven't played any games yet!"
            else:
                description = f'Rank: #{entry.place}\nHighest Score: {entry.highest_score}'

            embed, file = await self.create_embed(EmbedType.NORMAL, f"🎮 {ctx.author.name}'s Stats", description)
            await ctx.send(embed=embed, file=file)

        except Exception as e:
            logger.error(f'Error showing score: {e}')
            await ctx.send('An error occurred while fetching your score.')

    async def _run_countdown(self, channel_id: int, message: discord.Message) -> None:
        """
        Run the countdown timer before game start with visual progress bar.

        Updates the message every second with the current countdown status.

        Args:
            channel_id (int): ID of the channel where the game is running
            message (discord.Message): The message to update with countdown progress

        Raises:
            Exception: If there's an error during the countdown process
        """
        try:
            for countdown in range(self.service.LOADING_TIME, -1, -1):
                if not message:
                    logger.error('Message was deleted during countdown')
                    return

                total_width = 20
                filled = round((countdown / self.service.LOADING_TIME) * total_width)
                progress_bar = f'`{"█" * filled}{"░" * (total_width - filled)}`'

                player_names = (f'<@{player_id}>' for player_id in self.service.get_game(channel_id).players.keys())

                embed, _ = await self.create_embed(
                    type=EmbedType.NORMAL,
                    title='🎮 Guess The Anime Quiz',
                    description=(f'Game starting in `{countdown}` seconds!\n{progress_bar}\n\nPlayer(s): {", ".join(player_names)}\n\nPress the button to join!'),
                )

                await message.edit(embed=embed)
                await asyncio.sleep(1)

            game = self.service.get_game(channel_id)
            if not game:
                logger.error(f'No game found for channel {channel_id} after countdown')
                return

            if not game.players:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send('Game cancelled - no players joined!')
                logger.warning(f'No players joined game in channel {channel_id}')
                return

            logger.info(f'Starting game in channel {channel_id} with {len(game.players)} players')
            if not self.service.start_game(channel_id):
                logger.error(f'Failed to start game in channel {channel_id}')
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send('Failed to start game - please try again!')
                return

            await self._run_game(channel_id)

        except asyncio.CancelledError:
            logger.info(f'Countdown cancelled for channel {channel_id}')
        except Exception as e:
            logger.error(f'Error in countdown: {e}', exc_info=True)
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send('An error occurred while starting the game.')
        finally:
            if channel_id in self.active_countdowns:
                del self.active_countdowns[channel_id]

    async def _run_game(self, channel_id: int) -> None:
        """
        Main game loop that handles rounds, answers, and game completion.

        Manages the flow of the game, including displaying questions, handling answers,
        and determining when the game ends.

        Args:
            channel_id (int): ID of the channel where the game is running

        Raises:
            Exception: If there's an error during game execution
        """
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        try:
            while True:
                self.service.start_next_round(channel_id)

                try:
                    (
                        image_file,
                        options,
                        correct_answer,
                    ) = await self.service.get_round_data(channel_id)
                    if not image_file:
                        await channel.send('Failed to load image for this round. Trying next round...')
                        continue

                    game = self.service.get_game(channel_id)
                    current_round_difficulty = self.service.get_current_difficulty(game)
                    game.round_feedback.append(f'The correct answer was: **{correct_answer}**')

                    logger.info(f'Round started - Channel: {channel_id}')
                    logger.info(f'Correct answer is: {correct_answer}')
                    logger.info(f'Round difficulty: {current_round_difficulty}')
                except ValueError as e:
                    await channel.send(f'Error: {e}')
                    break

                view = AnswerView(self, options, correct_answer)

                base_embed = await self._create_round_embed(
                    channel_id,
                    options,
                    self.service.ROUND_TIME,
                )

                round_msg = await channel.send(embed=base_embed, file=image_file, view=view)

                for i in range(self.service.ROUND_TIME - 1, -1, -1):
                    if self.service.have_all_players_answered(channel_id):
                        logger.info('Round ended early - all players answered')
                        break

                    await asyncio.sleep(1)
                    try:
                        updated_embed = await self._create_round_embed(channel_id, options, i, base_embed=round_msg.embeds[0])
                        await round_msg.edit(embed=updated_embed)
                    except discord.NotFound:
                        break

                timed_out_players = self.service.handle_game_timeout(channel_id)
                if timed_out_players:
                    timeout_messages = ["⏰ Time's up!"]
                    for player_name, lives in timed_out_players:
                        hearts = '❤️' * lives
                        status = 'has been eliminated! 💀' if lives <= 0 else f'has {hearts} remaining'
                        timeout_messages.append(f"⚠️ {player_name} didn't answer and {status}")
                    await channel.send('\n'.join(timeout_messages))

                await channel.send('\n'.join(game.round_feedback))

                is_game_over, final_scores = self.service.check_game_over(channel_id)
                if is_game_over:
                    await self._show_game_results(channel, final_scores)
                    self.service.cleanup_game(channel_id)
                    break

                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f'Error in game loop: {e}', exc_info=True)
            await channel.send('An error occurred during the game.')
            self.service.cleanup_game(channel_id)

    async def _handle_answer(self, interaction: discord.Interaction, answer: str, correct_answer: str) -> None:
        """
        Process a player's answer and provide feedback.

        Handles the game logic when a player submits an answer, including:
        - Validating the answer timing
        - Processing the answer correctness
        - Updating player scores and lives
        - Providing appropriate feedback

        Args:
            interaction (discord.Interaction): The button interaction that triggered the answer
            answer (str): The player's chosen answer
            correct_answer (str): The correct answer for the current round

        Raises:
            Exception: If there's an error processing the answer
        """
        game_state = None
        try:
            game_state = self.service.get_game(interaction.channel.id)
            if not game_state:
                await interaction.response.send_message('No active game found!', ephemeral=True)
                return

            if interaction.user.id in game_state.timed_out_players:
                await interaction.response.send_message('Your answer came too late!', ephemeral=True)
                return

            if game_state.processing_answers:
                await interaction.response.send_message('Processing another answer, please wait...', ephemeral=True)
                game_state.answered_players.remove(interaction.user.id)
                return

            game_state.processing_answers = True

            is_correct, is_eliminated, new_high_score = self.service.process_answer(interaction.channel.id, interaction.user.id, answer, correct_answer)

            if is_correct:
                game_state.round_feedback.append(f'✅ {interaction.user.name} got it right!')
            else:
                player = game_state.players[interaction.user.id]
                if is_eliminated:
                    player = game_state.players[interaction.user.id]
                    elimination_message = f'❌ {interaction.user.name} got it wrong and has been eliminated! 💀'
                    if player.pending_high_score:
                        elimination_message += f'\n🏆 They achieved a new high score of {player.pending_high_score}!'
                    game_state.round_feedback.append(elimination_message)
                else:
                    hearts = '❤️' * player.lives
                    game_state.round_feedback.append(f'❌ {interaction.user.name} got it wrong and has {hearts} remaining.')

        except Exception as e:
            logger.error(f'Error handling answer: {e}', exc_info=True)
            try:
                await interaction.response.send_message('An error occurred processing your answer.', ephemeral=True)
            except discord.errors.InteractionResponded:
                await interaction.followup.send('An error occurred processing your answer.', ephemeral=True)
        finally:
            if game_state:
                game_state.processing_answers = False

    async def _show_game_results(self, channel: discord.TextChannel, final_scores: Optional[Dict[int, int]]) -> None:
        """
        Display the final results of a completed game.

        Creates and sends an embed showing the final ranking and scores of all players
        who participated in the game.

        Args:
            channel (discord.TextChannel): The channel where the game was played
            final_scores (Optional[Dict[int, int]]): Dictionary mapping player IDs to their final scores

        Note:
            Top 3 players are highlighted with medals (gold, silver, bronze)
        """
        if not final_scores:
            return

        game = self.service.get_game(channel.id)
        if not game:
            return

        sorted_scores = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

        description = []
        for i, (player_id, score) in enumerate(sorted_scores, 1):
            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, '🎮')
            member = channel.guild.get_member(player_id)
            player_name = member.name if member else f'Player {player_id}'
            player = game.players[player_id]
            score_text = f'{medal} {player_name}: {score} points'
            if player.pending_high_score:
                score_text += ' 🏆 New Personal Best!'
            description.append(score_text)

        embed = discord.Embed(
            title='🎮 Game Over!',
            description='\n'.join(description),
            color=discord.Color.gold(),
        )
        await channel.send(embed=embed)

    async def _create_round_embed(
        self,
        channel_id: int,
        options: List[str],
        time_left: int,
        base_embed: Optional[discord.Embed] = None,
    ) -> discord.Embed:
        """
        Create or update the embed for the current game round.

        Args:
            channel_id (int): ID of the channel where the game is running
            options (List[str]): List of possible answers
            time_left (int): Seconds remaining in the round
            base_embed (Optional[discord.Embed]): Existing embed to update

        Returns:
            discord.Embed: The created or updated embed

        Raises:
            ValueError: If no active game is found for the channel
        """
        game = self.service.get_game(channel_id)
        if not game:
            raise ValueError('No active game found')

        def create_player_status() -> str:
            status = []
            for player in game.players.values():
                hearts = '❤️' * player.lives
                status.append(f'{player.name}: {hearts} (Score: {player.score})')
            return '\n'.join(status)

        def create_timer_footer() -> str:
            timer_bar = '█' * (time_left // 2) + '░' * (5 - (time_left // 2))
            diff_display = {
                'easy': 'Easy 🟢',
                'medium': 'Medium 🟡',
                'hard': 'Hard 🔴',
            }.get(game.current_round_difficulty, 'Normal ⚪')
            return f'Time: {time_left}s {timer_bar} | Difficulty: {diff_display}'

        if base_embed:
            embed = base_embed
            if len(embed.fields) > 1:
                embed.remove_field(1)
        else:
            embed = discord.Embed(title='🎯 Guess The Anime!', color=EmbedColor.NORMAL)

            option_text = '\n'.join(f'{i + 1}️⃣ {opt}' for i, opt in enumerate(options))
            embed.add_field(name='Options', value=option_text, inline=False)

        embed.add_field(name='Players', value=create_player_status(), inline=False)
        embed.set_footer(text=create_timer_footer())

        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(GTAQuizCog(bot))
