import os
import sys
import logging
import colorlog
import discord
from discord.ext import commands


class PatsBot:
    def __init__(self):
        intents = discord.Intents.default()
        # intents.guilds = True
        # intents.guild_messages = True
        # intents.messages = True
        # intents.reactions = True
        # intents.members = True
        # intents.message_content = True

        self.bot = commands.Bot(command_prefix="^", intents=intents)
        self.bot.remove_command("help")
        self.version = str(os.environ.get("GIT_COMMIT", "dev"))

    def run(self):
        self.bot.run(os.environ.get("DISCORD_TOKEN", ""))
