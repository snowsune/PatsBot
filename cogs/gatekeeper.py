import discord
import asyncio
from discord.ext import commands, tasks
from discord import app_commands
import logging
from datetime import datetime, timedelta, timezone
from PatsBot.models import TrackedUser, Base, KeyValue
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from utilities.guild_settings import (
    get_guild_setting,
    set_guild_setting,
    ensure_guild_exists,
)

REQUIRED_ROLE = os.environ.get("REQUIRED_ROLE", "Verified")
GRACE_PERIOD = timedelta(days=3)

# Use the same DB URL logic as Alembic
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./.local.sqlite"
engine = create_engine(DATABASE_URL, future=True)
Session = sessionmaker(bind=engine)


class Gatekeeper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.check_users_loop.start()

    def get_gatekeeper_enabled(self, guild_id: int) -> bool:
        """Check if gatekeeper is enabled for a guild."""
        return get_guild_setting(guild_id, "gatekeeper_enabled", False)

    def get_admin_channel(self, guild_id: int) -> int:
        """Get the admin channel for a guild from guild settings."""
        return get_guild_setting(guild_id, "gatekeeper_admin_channel")

    def get_required_role(self, guild_id: int) -> str:
        """Get the required role for a guild from guild settings."""
        return get_guild_setting(guild_id, "gatekeeper_required_role")

    async def sync_guild_members(self, guild):
        """Sync members from a specific guild to the database."""
        self.logger.info(f"Syncing members from guild: {guild.name}")
        new_users = 0
        async for member in guild.fetch_members(limit=None):
            if self.sync_member(member):
                new_users += 1
        self.logger.info(f"Synced {new_users} new users from {guild.name}")
        return new_users

    @app_commands.command(name="manage_gatekeeper")
    @app_commands.describe(
        action="Enable or disable gatekeeper",
        admin_channel="The channel where gatekeeper warnings will be posted (optional when disabling)",
        required_role="The role users must have to avoid being kicked (optional when disabling)",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="enable", value="enable"),
            app_commands.Choice(name="disable", value="disable"),
        ]
    )
    async def manage_gatekeeper(
        self,
        interaction: discord.Interaction,
        action: str,
        admin_channel: discord.TextChannel = None,
        required_role: discord.Role = None,
    ):
        """Manage gatekeeper for this server (Admin only)"""
        # Check if user is admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True,
            )
            return

        try:
            # Ensure guild exists in database
            ensure_guild_exists(interaction.guild_id, interaction.guild.name)

            if action == "enable":
                # Require both parameters when enabling
                if not admin_channel or not required_role:
                    await interaction.response.send_message(
                        "Both admin_channel and required_role are required when enabling gatekeeper.",
                        ephemeral=True,
                    )
                    return

                # Enable gatekeeper and set settings
                set_guild_setting(interaction.guild_id, "gatekeeper_enabled", True)
                set_guild_setting(
                    interaction.guild_id, "gatekeeper_admin_channel", admin_channel.id
                )
                set_guild_setting(
                    interaction.guild_id, "gatekeeper_required_role", required_role.name
                )

                # Sync members from this guild now that it's enabled
                await interaction.response.send_message(
                    f"Gatekeeper enabled! Admin channel: {admin_channel.mention}, Required role: {required_role.mention}\nSyncing members...",
                    ephemeral=True,
                )

                # Sync members in background
                new_users = await self.sync_guild_members(interaction.guild)
                await interaction.followup.send(
                    f"Synced {new_users} new users from {interaction.guild.name}",
                    ephemeral=True,
                )

            elif action == "disable":
                # Disable gatekeeper
                set_guild_setting(interaction.guild_id, "gatekeeper_enabled", False)

                await interaction.response.send_message(
                    "Gatekeeper disabled for this server.", ephemeral=True
                )

        except Exception as e:
            self.logger.error(f"Error managing gatekeeper: {e}")
            await interaction.response.send_message(
                "Error managing gatekeeper. Please try again.", ephemeral=True
            )

    @commands.Cog.listener()
    async def on_ready(self):
        # Create guild records for all guilds the bot is in
        self.logger.info("Creating guild records...")
        for guild in self.bot.guilds:
            ensure_guild_exists(guild.id, guild.name)

        # Only sync members from guilds where gatekeeper is enabled
        self.logger.info("Syncing members from enabled gatekeeper guilds...")
        total_new_users = 0
        for guild in self.bot.guilds:
            if self.get_gatekeeper_enabled(guild.id):
                new_users = await self.sync_guild_members(guild)
                total_new_users += new_users
            else:
                self.logger.info(
                    f"Skipping guild {guild.name} (gatekeeper not enabled)"
                )

        self.logger.info(
            f"Sync complete. {total_new_users} total new users from enabled guilds."
        )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.logger.info(f"New member joined: {member.id}")
        self.sync_member(member)

    def sync_member(
        self, member
    ) -> bool:  # Returns True if new user, False if existing user
        # Skip bots and admins
        if member.bot or member.guild_permissions.administrator:
            return False

        session = Session()
        try:
            user = session.get(TrackedUser, str(member.id))
            if not user:
                user = TrackedUser(
                    user_id=str(member.id),
                    joined_at=member.joined_at or datetime.utcnow(),
                    roles=",".join(
                        [role.name for role in member.roles if role.name != "@everyone"]
                    ),
                )
                session.add(user)
                session.commit()
            else:
                return False  # Existing user
        except Exception as e:
            self.logger.error(f"Error syncing member {member.id}: {e}")
        finally:
            session.close()
        return True  # New user

    @tasks.loop(seconds=10)
    async def check_users_loop(self):
        session = Session()
        try:
            now = datetime.utcnow()
            for user in session.query(TrackedUser).all():
                # Find the guild and member
                for guild in self.bot.guilds:
                    # Check if gatekeeper is enabled for this guild
                    if not self.get_gatekeeper_enabled(guild.id):
                        continue

                    # Check if admin channel and required role are configured
                    admin_channel_id = self.get_admin_channel(guild.id)
                    required_role_name = self.get_required_role(guild.id)

                    if not admin_channel_id or not required_role_name:
                        # Skip this guild if not properly configured
                        continue

                    admin_channel = guild.get_channel(admin_channel_id)
                    if not admin_channel:
                        # Skip if admin channel doesn't exist
                        continue

                    member = guild.get_member(int(user.user_id))
                    if not member:
                        continue
                    # Skip bots and admins
                    if member.bot or member.guild_permissions.administrator:
                        continue

                    # Check if user is marked for removal
                    if user.marked_for_removal:
                        try:
                            # await member.kick(reason="Not verified after grace period.")
                            user.kicked_at = now
                            session.commit()
                            self.logger.info(f"Kicked user {user.user_id}")

                            if admin_channel:
                                await admin_channel.send(
                                    f"Kicked user <@{user.user_id}> for not verifying."
                                )

                            # Sleep for 30 seconds to avoid rate limiting
                            await asyncio.sleep(30)
                        except Exception as e:
                            self.logger.error(f"Failed to kick {user.user_id}: {e}")
                        continue

                    # Check if user is past grace period and missing role
                    joined = user.joined_at or now  # When they joined the server
                    has_role = any(
                        r.name == required_role_name for r in member.roles
                    )  # Do they have the role we care about?

                    # If they don't have the role and have been here longer than the grace period, mark them for removal
                    if not has_role and now - joined > GRACE_PERIOD:
                        user.marked_for_removal = True  # Mark them for removal
                        session.commit()

                        # Post a warning in the admin channel if it exists
                        if admin_channel:
                            await admin_channel.send(
                                f"User <@{user.user_id}> has been absent the role {required_role_name} for {(now - joined).days} days and {((now - joined).seconds // 3600)} hours."
                            )
                        self.logger.info(f"Marked user {user.user_id} for removal.")
        finally:
            session.close()


async def setup(bot):
    await bot.add_cog(Gatekeeper(bot))
