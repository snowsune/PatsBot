import discord
import asyncio
from discord.ext import commands, tasks
from discord import app_commands
import logging
from datetime import datetime, timedelta, timezone
from PatsBot.models import TrackedUser, Base, KeyValue, RemovalStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from utilities.guild_settings import (
    get_guild_setting,
    set_guild_setting,
    ensure_guild_exists,
)
from utilities.removal_workflow import RemovalWorkflow

REQUIRED_ROLE = os.environ.get("REQUIRED_ROLE", "Verified")
GRACE_PERIOD = timedelta(days=3)

# Dry run mode - set to True to prevent actual DMs and kicks
DRY_RUN_MODE = os.environ.get("DRY_RUN_MODE", "false").lower() == "true"

# Use the same DB URL logic as Alembic
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./.local.sqlite"
engine = create_engine(DATABASE_URL, future=True)
Session = sessionmaker(bind=engine)


class Gatekeeper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

        if DRY_RUN_MODE:
            self.logger.warning(
                "🚨 DRY RUN MODE ENABLED - No actual DMs or kicks will be sent!"
            )

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
            if self.sync_member(member, initial_sync=True):
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

        # Start the removal check loop after bot is ready
        self.removal_check_loop.start()
        self.logger.info("Started removal check loop")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.logger.info(f"New member joined: {member.id}")
        self.sync_member(member, initial_sync=False)

    def sync_member(self, member, initial_sync=False) -> bool:
        """Sync a member to the database. Returns True if new user, False if existing user."""
        # Skip bots and admins
        if member.bot or member.guild_permissions.administrator:
            return False

        session = Session()
        try:
            user = session.get(TrackedUser, str(member.id))
            if not user:
                user = TrackedUser(
                    user_id=str(member.id),
                    guild_id=str(member.guild.id),
                    joined_at=(
                        datetime.utcnow()
                        if initial_sync
                        else (member.joined_at or datetime.utcnow())
                    ),
                    roles=",".join(
                        [role.name for role in member.roles if role.name != "@everyone"]
                    ),
                    removal_status=RemovalStatus.ACTIVE,
                )
                session.add(user)
                session.commit()
                return True  # New user
            else:
                # Update existing user's guild_id if needed
                if user.guild_id != str(member.guild.id):
                    user.guild_id = str(member.guild.id)
                    session.commit()
                return False  # Existing user
        except Exception as e:
            self.logger.error(f"Error syncing member {member.id}: {e}")
            return False
        finally:
            session.close()

    async def send_first_warning(self, guild, user, admin_channel):
        """Send the first warning to a user and post to admin channel."""
        try:
            # Send DM to user (or simulate in dry run)
            member = guild.get_member(int(user.user_id))
            if member:
                if DRY_RUN_MODE:
                    dm_message_id = f"DRY_RUN_{datetime.utcnow().timestamp()}"
                    self.logger.info(
                        f"[DRY RUN] Would send first warning DM to {user.user_id}"
                    )
                else:
                    dm_message = await member.send(
                        f"You have been marked for removal from **{guild.name}** because you haven't verified.\n"
                        f"You have **7 days** to get the required role or you will be removed from the server.\n"
                        f"Please contact a server administrator if you need help."
                    )
                    dm_message_id = str(dm_message.id)

                # Post to admin channel
                dry_run_prefix = "[DRY RUN] " if DRY_RUN_MODE else ""
                admin_message = await admin_channel.send(
                    f"{dry_run_prefix}⚠️ **First Warning Sent**\n"
                    f"User: <@{user.user_id}>\n"
                    f"Reason: Not verified after grace period\n"
                    f"Removal date: <t:{int(user.removal_date.timestamp())}:F>\n"
                    f"DM Message ID: {dm_message_id}"
                )

                # Update database
                session = Session()
                try:
                    RemovalWorkflow.mark_first_warning_sent(
                        session, user.user_id, dm_message_id
                    )
                finally:
                    session.close()

                self.logger.info(
                    f"{'[DRY RUN] ' if DRY_RUN_MODE else ''}Sent first warning to user {user.user_id}"
                )

        except Exception as e:
            self.logger.error(f"Failed to send first warning to {user.user_id}: {e}")
            # Still post to admin channel about the failure
            await admin_channel.send(
                f"❌ **Failed to send first warning**\n"
                f"User: <@{user.user_id}>\n"
                f"Error: {str(e)}"
            )

    async def send_final_notice(self, guild, user, admin_channel):
        """Send the final notice to a user and post to admin channel."""
        try:
            # Send DM to user (or simulate in dry run)
            member = guild.get_member(int(user.user_id))
            if member:
                if DRY_RUN_MODE:
                    dm_message_id = f"DRY_RUN_{datetime.utcnow().timestamp()}"
                    self.logger.info(
                        f"[DRY RUN] Would send final notice DM to {user.user_id}"
                    )
                else:
                    dm_message = await member.send(
                        f"⚠️ **FINAL WARNING**\n"
                        f"You have **2 days** remaining to verify in **{guild.name}** or you will be removed.\n"
                        f"This is your final notice. Please contact a server administrator immediately if you need help."
                    )
                    dm_message_id = str(dm_message.id)

                # Post to admin channel
                dry_run_prefix = "[DRY RUN] " if DRY_RUN_MODE else ""
                admin_message = await admin_channel.send(
                    f"{dry_run_prefix}🚨 **Final Notice Sent**\n"
                    f"User: <@{user.user_id}>\n"
                    f"Removal date: <t:{int(user.removal_date.timestamp())}:F>\n"
                    f"DM Message ID: {dm_message_id}"
                )

                # Update database
                session = Session()
                try:
                    RemovalWorkflow.mark_final_notice_sent(
                        session, user.user_id, dm_message_id
                    )
                finally:
                    session.close()

                self.logger.info(
                    f"{'[DRY RUN] ' if DRY_RUN_MODE else ''}Sent final notice to user {user.user_id}"
                )

        except Exception as e:
            self.logger.error(f"Failed to send final notice to {user.user_id}: {e}")
            # Still post to admin channel about the failure
            await admin_channel.send(
                f"❌ **Failed to send final notice**\n"
                f"User: <@{user.user_id}>\n"
                f"Error: {str(e)}"
            )

    async def remove_user(self, guild, user, admin_channel):
        """Remove a user from the guild and post to admin channel."""
        try:
            # Send final DM (or simulate in dry run)
            member = guild.get_member(int(user.user_id))
            if member:
                if DRY_RUN_MODE:
                    dm_message_id = f"DRY_RUN_{datetime.utcnow().timestamp()}"
                    self.logger.info(
                        f"[DRY RUN] Would send removal DM and kick user {user.user_id}"
                    )
                else:
                    dm_message = await member.send(
                        f"🚫 **You have been removed from {guild.name}**\n"
                        f"You failed to verify within the required timeframe.\n"
                        f"If you believe this was an error, please contact a server administrator."
                    )
                    dm_message_id = str(dm_message.id)

                    # Kick the user
                    await member.kick(reason="Not verified after removal period")

                # Post to admin channel
                dry_run_prefix = "[DRY RUN] " if DRY_RUN_MODE else ""
                admin_message = await admin_channel.send(
                    f"{dry_run_prefix}🚫 **User Removed**\n"
                    f"User: <@{user.user_id}>\n"
                    f"Reason: Not verified after removal period\n"
                    f"Removal time: <t:{int(datetime.utcnow().timestamp())}:F>\n"
                    f"DM Message ID: {dm_message_id}"
                )

                # Update database
                session = Session()
                try:
                    RemovalWorkflow.mark_user_removed(
                        session, user.user_id, dm_message_id
                    )
                finally:
                    session.close()

                self.logger.info(
                    f"{'[DRY RUN] ' if DRY_RUN_MODE else ''}Removed user {user.user_id}"
                )

        except Exception as e:
            self.logger.error(f"Failed to remove user {user.user_id}: {e}")
            # Still post to admin channel about the failure
            await admin_channel.send(
                f"❌ **Failed to remove user**\n"
                f"User: <@{user.user_id}>\n"
                f"Error: {str(e)}"
            )

    @tasks.loop(seconds=30)  # Check every 30 seconds
    async def removal_check_loop(self):
        """Main loop that checks for users needing removal actions."""
        self.logger.info("🔄 Removal check loop running...")
        self.logger.info(f"Found {len(self.bot.guilds)} guilds to check")
        session = Session()
        try:
            for guild in self.bot.guilds:
                self.logger.info(f"Checking guild: {guild.name} ({guild.id})")
                # Check if gatekeeper is enabled for this guild
                if not self.get_gatekeeper_enabled(guild.id):
                    self.logger.info(f"Gatekeeper not enabled for {guild.name}")
                    continue

                # Check if admin channel and required role are configured
                admin_channel_id = self.get_admin_channel(guild.id)
                required_role_name = self.get_required_role(guild.id)

                self.logger.info(
                    f"Admin channel: {admin_channel_id}, Required role: {required_role_name}"
                )

                if not admin_channel_id or not required_role_name:
                    self.logger.info(f"Missing configuration for {guild.name}")
                    continue

                admin_channel = guild.get_channel(admin_channel_id)
                if not admin_channel:
                    self.logger.info(
                        f"Admin channel {admin_channel_id} not found in {guild.name}"
                    )
                    continue

                guild_id_str = str(guild.id)
                now = datetime.utcnow()

                # Check for users who need first warnings
                users_needing_first_warning = (
                    RemovalWorkflow.get_users_needing_first_warning(
                        session, guild_id_str
                    )
                )

                for user in users_needing_first_warning:
                    await self.send_first_warning(guild, user, admin_channel)
                    await asyncio.sleep(2)  # Small delay to avoid rate limiting

                # Check for users who need final notices
                users_needing_final_notice = (
                    RemovalWorkflow.get_users_needing_final_notice(
                        session, guild_id_str
                    )
                )

                for user in users_needing_final_notice:
                    await self.send_final_notice(guild, user, admin_channel)
                    await asyncio.sleep(2)  # Small delay to avoid rate limiting

                # Check for users ready for removal
                users_ready_for_removal = RemovalWorkflow.get_users_ready_for_removal(
                    session, guild_id_str
                )

                for user in users_ready_for_removal:
                    await self.remove_user(guild, user, admin_channel)
                    await asyncio.sleep(5)  # Longer delay for removals

                # Check for users who should be marked for removal
                for user in (
                    session.query(TrackedUser)
                    .filter(
                        TrackedUser.guild_id == guild_id_str,
                        TrackedUser.removal_status == RemovalStatus.ACTIVE,
                    )
                    .all()
                ):
                    member = guild.get_member(int(user.user_id))
                    if not member:
                        continue

                    # Skip bots and admins
                    if member.bot or member.guild_permissions.administrator:
                        continue

                    # Check if user is past grace period and missing role
                    joined = user.joined_at or now
                    has_role = any(r.name == required_role_name for r in member.roles)

                    # If they don't have the role and have been here longer than the grace period, mark them for removal
                    if not has_role and now - joined > GRACE_PERIOD:
                        RemovalWorkflow.mark_user_for_removal(
                            session, user.user_id, guild_id_str
                        )

                        # Post initial warning to admin channel
                        dry_run_prefix = "[DRY RUN] " if DRY_RUN_MODE else ""
                        await admin_channel.send(
                            f"{dry_run_prefix}⚠️ **User Marked for Removal**\n"
                            f"User: <@{user.user_id}>\n"
                            f"Reason: Not verified after grace period\n"
                            f"Grace period exceeded by: {(now - joined - GRACE_PERIOD).days} days\n"
                            f"First warning will be sent automatically."
                        )

                        self.logger.info(
                            f"{'[DRY RUN] ' if DRY_RUN_MODE else ''}Marked user {user.user_id} for removal"
                        )

        except Exception as e:
            self.logger.error(f"Error in removal check loop: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            session.close()

    @app_commands.command(name="removal_status")
    @app_commands.describe(
        user="The user to check removal status for (optional, shows guild summary if not provided)"
    )
    async def removal_status(
        self, interaction: discord.Interaction, user: discord.Member = None
    ):
        """Check removal status for a user or guild summary (Admin only)"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True,
            )
            return

        session = Session()
        try:
            guild_id_str = str(interaction.guild.id)

            if user:
                # Check specific user
                tracked_user = RemovalWorkflow.get_user_status(session, str(user.id))
                if tracked_user:
                    status_emoji = {
                        RemovalStatus.ACTIVE: "✅",
                        RemovalStatus.PENDING_REMOVAL: "⏳",
                        RemovalStatus.FIRST_WARNING_SENT: "⚠️",
                        RemovalStatus.FINAL_NOTICE_SENT: "🚨",
                        RemovalStatus.REMOVED: "🚫",
                    }

                    embed = discord.Embed(
                        title=f"Removal Status for {user.display_name}",
                        color=discord.Color.blue(),
                    )
                    embed.add_field(
                        name="Status",
                        value=f"{status_emoji[tracked_user.removal_status]} {tracked_user.removal_status.value}",
                        inline=True,
                    )
                    embed.add_field(
                        name="Joined",
                        value=f"<t:{int(tracked_user.joined_at.timestamp())}:F>",
                        inline=True,
                    )

                    if tracked_user.removal_date:
                        embed.add_field(
                            name="Removal Date",
                            value=f"<t:{int(tracked_user.removal_date.timestamp())}:F>",
                            inline=True,
                        )

                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(
                        f"No tracking data found for {user.display_name}",
                        ephemeral=True,
                    )
            else:
                # Show guild summary
                summary = RemovalWorkflow.get_removal_summary(session, guild_id_str)

                embed = discord.Embed(
                    title=f"Removal Status Summary for {interaction.guild.name}",
                    color=discord.Color.blue(),
                )
                embed.add_field(
                    name="Total Tracked", value=summary["total_tracked"], inline=True
                )
                embed.add_field(name="✅ Active", value=summary["active"], inline=True)
                embed.add_field(
                    name="⏳ Pending Removal",
                    value=summary["pending_removal"],
                    inline=True,
                )
                embed.add_field(
                    name="⚠️ First Warning Sent",
                    value=summary["first_warning_sent"],
                    inline=True,
                )
                embed.add_field(
                    name="🚨 Final Notice Sent",
                    value=summary["final_notice_sent"],
                    inline=True,
                )
                embed.add_field(
                    name="🚫 Removed", value=summary["removed"], inline=True
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error checking removal status: {e}")
            await interaction.response.send_message(
                "Error checking removal status. Please try again.",
                ephemeral=True,
            )
        finally:
            session.close()

    @app_commands.command(name="reset_user_status")
    @app_commands.describe(user="The user to reset status for")
    async def reset_user_status(
        self, interaction: discord.Interaction, user: discord.Member
    ):
        """Reset a user's removal status to active (Admin only)"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True,
            )
            return

        session = Session()
        try:
            RemovalWorkflow.reset_user_status(session, str(user.id))

            await interaction.response.send_message(
                f"✅ Reset removal status for {user.display_name} to active.",
                ephemeral=True,
            )

            # Also post to admin channel if configured
            admin_channel_id = self.get_admin_channel(interaction.guild.id)
            if admin_channel_id:
                admin_channel = interaction.guild.get_channel(admin_channel_id)
                if admin_channel:
                    await admin_channel.send(
                        f"✅ **User Status Reset**\n"
                        f"User: <@{user.id}>\n"
                        f"Reset by: {interaction.user.mention}\n"
                        f"Status: Active"
                    )

        except Exception as e:
            self.logger.error(f"Error resetting user status: {e}")
            await interaction.response.send_message(
                "Error resetting user status. Please try again.",
                ephemeral=True,
            )
        finally:
            session.close()


async def setup(bot):
    await bot.add_cog(Gatekeeper(bot))
