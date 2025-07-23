import os
import sys
import logging
import colorlog
import discord
from discord.ext import commands
import asyncio


class PatsBot:
    def __init__(self):
        # Set up colorlog for colored logs
        handler = colorlog.StreamHandler()
        handler.setFormatter(
            colorlog.ColoredFormatter(
                "%(log_color)s%(levelname)s:%(name)s: %(message)s",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            )
        )
        debug_env = str(os.environ.get("DEBUG", "0")).lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        log_level = logging.DEBUG if debug_env else logging.INFO
        logging.basicConfig(level=log_level, handlers=[handler])

        # Mute discord.py logs except warnings/errors
        discord_logger = logging.getLogger("discord")
        discord_logger.setLevel(logging.WARNING)
        for h in discord_logger.handlers[:]:
            discord_logger.removeHandler(h)

        intents = discord.Intents.default()
        intents.message_content = True  # Required for command processing
        intents.members = True  # Required for member join/listen
        # Enable privileged intents only if needed in the future
        # intents.guilds = True
        # intents.guild_messages = True
        # intents.messages = True
        # intents.reactions = True
        # intents.members = True
        # intents.message_content = True

        self.bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
        self.bot.remove_command("help")
        self.version = str(os.environ.get("GIT_COMMIT", "dev"))

    async def load_cogs(self):
        logging.info("Loading cogs...")
        cogs_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "cogs"
        )
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.bot.load_extension(cog_name)
                    logging.info(f"Loaded cog: {cog_name}")
                except Exception as e:
                    logging.error(f"Failed to load cog {cog_name}: {e}")
        logging.info("Done loading cogs")

    def run(self):
        async def runner():
            await self.load_cogs()

            @self.bot.event
            async def on_ready():
                guild_id = os.environ.get("GUILD_ID")
                if guild_id:
                    try:
                        guild = discord.Object(id=int(guild_id))
                        await self.bot.tree.sync(guild=guild)
                        logging.info(f"Synced app commands to guild {guild_id}")
                    except Exception as e:
                        logging.error(
                            f"Failed to sync app commands to guild {guild_id}: {e}"
                        )
                else:
                    try:
                        await self.bot.tree.sync()
                        logging.info("Synced app commands globally")
                    except Exception as e:
                        logging.error(f"Failed to sync app commands globally: {e}")

            await self.bot.start(os.environ.get("DISCORD_TOKEN", ""))

        asyncio.run(runner())
