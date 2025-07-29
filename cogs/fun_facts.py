import discord
import logging
from discord.ext import commands
from discord import app_commands
import yaml
import random
import os
from pathlib import Path


class FunFactsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.facts = []
        self.load_facts()

    def load_facts(self):
        """Load fun facts from the YAML file"""
        try:
            # Get the path to the Data directory relative to the bot's main directory
            data_path = (
                Path(__file__).parent.parent / "PatsBot" / "Data" / "FunFacts.yaml"
            )

            if not data_path.exists():
                self.logger.warning(f"FunFacts.yaml not found at {data_path}")
                return

            with open(data_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
                self.facts = data.get("facts", [])

            self.logger.info(f"Loaded {len(self.facts)} fun facts")

        except Exception as e:
            self.logger.error(f"Error loading fun facts: {e}")
            self.facts = []

    @app_commands.command(name="fun_fact", description="Get a random fun fact!")
    async def fun_fact(self, interaction: discord.Interaction):
        """Send a random fun fact"""
        if not self.facts:
            await interaction.response.send_message(
                "❌ No fun facts available at the moment!", ephemeral=True
            )
            return

        # Get a random fact
        fact = random.choice(self.facts)

        # Create an embed for the fun fact
        embed = discord.Embed(
            title="Fun Fact!", description=fact, color=discord.Color.blue()
        )
        embed.set_footer(text="Use `/fun_fact` to get another random fact!")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(FunFactsCog(bot))
