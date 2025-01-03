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
* `kuso gtaquiz start`: Start a new GTA quiz game
* `kuso gtaquiz join`: Join an ongoing game before it starts
* `kuso gtaquiz stop`: Stop the current game

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

### Reminder Commands
Base command: `reminder` (alias: `rem`)
* `kuso reminder set <time> <message>`: Set a new reminder
  * Time format: `1h30m`, `2d`, `30m`
  * Examples:
    * `reminder set 1h30m Take a break`
    * `reminder set 2d Check emails`
* `kuso reminder list`: List all your active reminders
* `kuso reminder delete <index>` (aliases: `del`, `remove`): Delete a reminder by its index number

### Thread Commands
> [!IMPORTANT]
> Thread commands require the "Manage Threads" permission which is only given to certain people.

Base command: `thread`
* `kuso thread create <role> <name> [message]`: Create a private thread immediately
  * `role`: The role that can access the thread
  * `name`: Name of the thread
  * `message`: Optional initial message in the thread
  * Example:
    * `thread create @Kaoru Cult "romance manga" "The Fragrant Flower Blooms With Dignity slaps"`
* `kuso thread schedule <role> <time> <name> [message]`: Schedule a private thread for later
  * Time format: `1h30m`, `2d`, `30m`
  * Example:
    * `thread schedule @Book Club 2h "The Gunslinger" "Thread for The Gunslinger Discussion!"`
* `kuso thread list`: List all scheduled threads
* `kuso thread delete <id>` (aliases: `del`, `remove`): Delete a scheduled thread by its ID

### Food Counter Commands
* `kuso awaiz` (alias: `caseoh`): Increment food mention counter for Awaiz
* `kuso awaizcount` (alias: `drywall`): Display current food mention count for Awaiz