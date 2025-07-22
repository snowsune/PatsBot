import discord
import logging
import random
import asyncio
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime


class ToolCog(commands.Cog, name="ToolsCog"):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.command_counter = 0  # Initialize a command counter
        self.start_time = datetime.now()  # Track when the bot started
        self.bot.usage_today = self.command_counter

    @commands.Cog.listener()
    async def on_ready(self):
        self.update_status.start()
        self.reset_counter_task.start()

    @tasks.loop(minutes=1)
    async def update_status(self):
        statuses = [
            f"Bot is online!",
            f"Connected to {len(self.bot.guilds)} guilds",
            f"Commands run today: {self.command_counter}",
        ]
        new_status = random.choice(statuses)
        await self.bot.change_presence(activity=discord.Game(name=new_status))

    @commands.Cog.listener()
    async def on_app_command_completion(self, ctx, cmd):
        self.command_counter += 1
        self.bot.usage_today = self.command_counter

    @tasks.loop(seconds=1)
    async def reset_counter_task(self):
        while True:
            # Replace with your own logic for midnight reset
            await asyncio.sleep(86400)
            self.command_counter = 0
            self.bot.usage_today = self.command_counter
            self.logger.info("Command counter reset.")

    @app_commands.command(name="invite_bot")
    async def invite_bot(self, ctx: discord.Interaction):
        await ctx.response.send_message(
            f"Use this link to invite me to your server!",
            ephemeral=True,
        )

    @app_commands.command(name="version")
    async def version(self, ctx: discord.Interaction):
        await ctx.response.send_message(
            f"Bot version: {getattr(self.bot, 'version', 'unknown')}"
        )


async def setup(bot):
    await bot.add_cog(ToolCog(bot))
