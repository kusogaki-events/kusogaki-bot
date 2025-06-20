from typing import Dict, Optional, Tuple

from discord import Embed, File

from kusogaki_bot.shared import EmbedType, get_embed


class HelpService:
    def __init__(self):
        self.command_details: Dict = {
            'help': {
                'title': 'Help System',
                'description': """
Get information about bot commands and features.

**Usage:**
• `kuso help` - View bot overview
• `kuso help <command>` - Get detailed help for a specific command

**Example:**
```
kuso help poll
```
""",
            },
            'gtaquiz': {
                'title': 'GTA Quiz Game',
                'description': """
The GTA Quiz Game allows users to participate in GTA style quiz using all the previous season's images

**Subcommands:**
- `start [difficulty]` - Start a new game session. If difficulty is specified (easy/medium/hard), only images of that difficulty will appear. Leave it unspecified to experience progressive difficulty similar to GTA's adaptive system on AniList
- `stop` - Ends the current game session
- `leaderboard` - Display global leaderboard with top players
- `score` - Show your personal stats and rank

**Examples:**
```
kuso gtaquiz start medium
kuso gq stop
kuso gq leaderboard
```

**Aliases:** `gq`
""",
            },
            'poll': {
                'title': 'Poll System',
                'description': """
Create and manage polls. This command is restricted to staff members.

**Usage:**
`kuso poll <question> <duration> <multiple> <options...>`

**Parameters:**
• `question` - The poll question
• `duration` - Duration in hours
• `multiple` - Allow multiple choices (true/false)
• `options` - Space-separated poll options

**Related Commands:**
• `endpoll <question>` - End an active poll
• `listpolls` - Show all active polls

**Example:**
```
kuso poll "Favorite manga?" 24 false "One Piece" "Naruto" "Bleach"
```
""",
            },
            'awaiz': {
                'title': 'Food Counter',
                'description': """
Track food mentions for Awaiz.

**Commands:**
• `awaiz` - Increment the counter
• `awaizcount` - Display current count

**Aliases:**
• `awaiz` → `caseoh`
• `awaizcount` → `drywall`
""",
            },
            'recommend': {
                'title': 'Animanga Recommendations',
                'description': """
**Usage:**
`kuso recommend <anilist username> [genre] [media type]`

**Parameters:**
• `anilist username` - Anilist username to get recommendations for
• `genre` [Optional]- Obtains recommendations only from the genre if specified. If the genre has spaces, use quotes.
• `media type` [Optional] - Specify media type (anime or manga), defaults to anime

**Examples:**
```
kuso recommend garlic romance anime
kuso rec awaiz
kuso rec senescu "Slice of Life" manga
```

**Aliases:** rec
""",
            },
        }

    async def get_overview_embed(self) -> Tuple[Embed, Optional[File]]:
        """Generate the overview embed for the help command."""
        description = """
Welcome to the Kusogaki Bot! Here's a quick overview of what I can do:

* **GTA Quiz Game**: Run GTA style guessing game
* **Polls**: Create and manage polls (Staff only)
* **Food Counter**: Track food mentions
* **Recommendations**: Recommend anime and manga

### Command List
To see all available commands, click the `View all Commands` button below.

For detailed information about a command, use: `kuso help <command>`.
"""
        return await get_embed(EmbedType.NORMAL, 'Kusogaki Bot', description)

    async def get_all_commands_embed(self) -> Tuple[Embed, Optional[File]]:
        """Generate the embed containing all commands."""
        description = """
**Help Commands**
• `kuso help` - Show this help message
• `kuso help <command>` - Get detailed help for a command

**GTA Quiz Game Commands** (Base: `gtaquiz`, `gq`)
- `kuso gtaquiz start [difficulty]` - Start a new game. Optional difficulty (easy/medium/hard) for fixed difficulty mode
- `kuso gtaquiz join` - Join an ongoing game
- `kuso gtaquiz stop` - Stop the current game
- `kuso gtaquiz leaderboard` - View global rankings
- `kuso gtaquiz score` - Check your stats

**Poll Commands** (Staff Only)
• `kuso poll <question> <duration> <multiple> <options...>` - Create a poll
• `kuso endpoll <question>` - End an active poll
• `kuso listpolls` - List all active polls

**Food Counter Commands**
• `kuso awaiz` (alias: `caseoh`) - Increment food counter
• `kuso awaizcount` (alias: `drywall`) - Display current count

**Recommendation Commands**
• `kuso recommend (alias: `rec`) <anilist username> [genre] [media type]` - Recommend an anime/manga with optional genre
"""
        return await get_embed(EmbedType.INFORMATION, 'All Commands', description)

    async def get_command_help(
        self, command: str
    ) -> Optional[Tuple[Embed, Optional[File]]]:
        """Get detailed help for a specific command."""
        command = command.lower()
        if command in self.command_details:
            details = self.command_details[command]
            return await get_embed(
                EmbedType.INFORMATION, details['title'], details['description']
            )
        return None
