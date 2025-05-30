# Contributing - Development

So, you're making code changes: _bold_. Well, there's a bit of setup involved to test this locally!

> [!IMPORTANT]
> Make sure to consult the contributing guidelines proper to ensure you're following best practices!

## Table of Contents

## Prerequisites

### Python

Currently, this project is using version `3.12`.

### UV

uv is the tool we use for dependency management in this project. It's significantly faster than pip and other package managers, making dependency installation and environment management more efficient. While uv isn't mandatory, _**it's highly recommended**_ as it makes working with dependencies and environments more straightforward.

> [!NOTE]
> This guide will assume you're using uv. Please follow a similar approach with other dependency management tools for the steps that require it.

## Setup

There are two parts for setting up your local dev enviornment: **local development setup**, and **bot setup**.

### Local Development Setup
Use the following commands in your terminal (in order, waiting for the previous one to finish):

1. `uv venv`: Start a virtual environment with uv
2. `uv sync`: Sync the project's dependencies with the virtual environment
3. `pre-commit install`: This will install the pre-receive hooks for this project

#### Running the Bot

To run the bot, use the following command in the terminal:
```
uv run main.py
```

#### Development Mode

The bot includes a development mode with hot-reloading capability. When enabled, it watches your code files and automatically reloads modules when changes are detected. To use it:

1. Start the bot
2. Use the `kuso dev` command to toggle development mode
3. Make changes to your code - the bot will automatically reload affected modules

This eliminates the need to restart the bot after each code change during development.

### Bot Setup

> [!IMPORTANT]
> There are three commands used by the bot which require database access:  **the awaiz food tracker**, **gta quiz**, and **reminders**. If there is an issue with one of these commands, or if you'd like a change, you will need to submit a bug/feature request issue or make a support ticket/suggestion on the discord server.

#### Creating a Discord Application

In order for `kusogaki-botto` to use the Discord API, you will need to create a Discord bot it can run in. You can visit the [Discord Developer Portal](https://discord.com/developers/applications/)  and click `New Application`. You can edit the identification information of the bot (e.g., app name, app icon, etc.). On the `Bot` tab of the left navigation bar, you'll need to add the bot which will create a bot user that can be controlled by the code. Make sure to copy the bot token and store it somewhere for a later step. You will also need to enable the `Message Content` and `Presence` intents. Using the `Oauth2` tab, you should select `bot` scopes, and then paste the url in your browser to add it to your discord server for testing.

#### Configuration

The Kusogaki bot uses an `.env` file. Please create a `.env` file using the `.env.example` template. You can leave the database related information and staff role id blank (unless you're on the Kusogaki team).