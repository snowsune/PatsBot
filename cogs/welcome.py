import discord
from discord.ext import commands
import logging

WELCOME_CHANNEL_ID = 1136410197921898589  # Age verification channel
GUILD_ID = 945386790402023554
CHANNEL_LINK = f"https://discord.com/channels/{GUILD_ID}/{WELCOME_CHANNEL_ID}"
TRIGGER_ROLE_ID = 1136372559160545375


class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Only trigger when the user is given the trigger role
        before_roles = set(r.id for r in before.roles)
        after_roles = set(r.id for r in after.roles)
        if TRIGGER_ROLE_ID in after_roles and TRIGGER_ROLE_ID not in before_roles:
            try:
                welcome_message = (
                    f"Welcome {after.display_name} to the Azorewrath Server!\n"
                    f"If you want access to nsfw, please visit the age verification channel: {CHANNEL_LINK}\n"
                    f"Other than that, please enjoy your stay!"
                )
                await after.send(welcome_message)
                self.logger.info(
                    f"Sent welcome message to {after.display_name} ({after.id})"
                )
            except Exception as e:
                self.logger.warning(
                    f"Could not send welcome message to {after.display_name} ({after.id}): {e}"
                )


async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))
