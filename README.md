![](./static/githubbanner.png)
<br />

<h2> Status </h2>

![Status](https://img.shields.io/badge/Kusogaki%20Bot-Online-brightgreen?style=for-the-badge&logo=discord&logoColor=white)

<h2> Bug report or Feature request </h2>

If you encounter a bug or have a feature request, please [create an issue](https://github.com/kusogaki-events/kusogaki-bot/issues), or create a support ticket on the [support channel in our discord server](https://discord.com/channels/1204428205675651122/1204814321029488660)

<h2> Want to Contribute? </h2>

Refer to [CONTRIBUTING.md](https://github.com/kusogaki-events/kusogaki-bot/blob/main/docs/CONTRIBUTING.md)

<h2> Commands </h2>

### GTA Quiz Game Commands
Base command: `gtaquiz` (alias: `gq`)
* `kuso gtaquiz start [difficulty]`: Start a new game session. If difficulty is specified (easy/medium/hard), only images of that difficulty will appear. Leave it unspecified to experience progressive difficulty similar to GTA's adaptive system on AniList
* `kuso gtaquiz stop`: Stop the current game
* `kuso gtaquiz leaderboard`: View global rankings
* `kuso gtaquiz score`: Check your stats

### Food Counter Commands
* `kuso awaiz` (alias: `caseoh`): Manually increment the food mention counter for Awaiz
* `kuso awaizcount` (alias: `drywall`): Display current food mention count for Awaiz

### Poll Commands
> [!IMPORTANT]
> Poll commands are only usable by Kusogaki staff.

* `kuso poll <question> <duration> <multiple> <options...>`: Create a new poll
  * `question`: The poll question
  * `duration`: Duration in hours
  * `multiple`: Allow multiple choices (true/false)
  * `options`: Poll options (space-separated)
* `kuso endpoll <question>`: End an active poll
* `kuso listpolls`: List all active polls

### Animanga Recommendation Commands
* `recommend <username> [genre] [anime/manga]` (alias: `rec`):
  * `question`: Anilist username to provide recommendations for
  * `genre`: If specified, limit recommendations to a specific genre
  * `anime/manga`: Specify to recommend anime or manga (defaults to anime)
