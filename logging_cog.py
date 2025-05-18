import discord
from discord.ext import commands
from discord.utils import escape_markdown, escape_mentions

LOG_CHANNEL_NAME = "🐢・server-logs" # Name of the Logging channel. Change Name for your Server.

class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self, guild: discord.Guild):
        return discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)

    def create_embed(self, title, description, color=discord.Color.blurple(), user=None, thumbnail=True):
        embed = discord.Embed(title=title, description=description, color=color)
        if user:
            embed.set_author(name=str(user), icon_url=user.display_avatar.url)
            embed.set_footer(text=f"{user} | {user.id}")
        
            if thumbnail:
                embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    # --- Member joined ---
    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.get_log_channel(member.guild)
        if channel:
            embed = self.create_embed("📥 Member Joined", f"{member.mention} joined the server.", discord.Color.green(), member)
            await channel.send(embed=embed)

    # --- Member left ---
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = self.get_log_channel(member.guild)
        if channel:
            embed = self.create_embed("📤 Member Left", f"{member.mention} left or was kicked from the server.", discord.Color.red(), member)
            await channel.send(embed=embed)

    # --- Single message deleted ---
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild and not message.author.bot:
            channel = self.get_log_channel(message.guild)
            if channel:
                embed = self.create_embed(
                    "🗑️ Message Deleted",
                    f"**Author:** {message.author.mention}\n"
                    f"**Channel:** {message.channel.mention}\n\n"
                    f"{message.content or '*No content (e.g. embed or attachment)*'}",
                    discord.Color.red(),
                    message.author
                )
                await channel.send(embed=embed)


    # --- Bulk messages deleted ---
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if not messages:
            return
        guild = messages[0].guild
        if guild is None:
            return
        channel = self.get_log_channel(guild)
        if not channel:
            return
        
        log_channel_name = messages[0].channel.mention if messages[0].channel else "Unknown channel"
        count = len(messages)

        embed = discord.Embed(
            title="🗑️ Bulk Messages Deleted",
            description=f"{count} messages were deleted in {log_channel_name}.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Bulk delete event")

        await channel.send(embed=embed)

    # --- Message edited ---
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.guild and not before.author.bot and before.content != after.content:
            channel = self.get_log_channel(before.guild)
            if channel:
                before_content = before.content or "*Empty message*"
                after_content = after.content or "*Empty message*"

                max_length = 1024
                if len(before_content) > max_length:
                    before_content = before_content[:max_length] + "... (truncated)"
                if len(after_content) > max_length:
                    after_content = after_content[:max_length] + "... (truncated)"

                embed = self.create_embed(
                    "",
                    f"**Message Edited in** {before.channel.mention} [Jump to Message]({after.jump_url})\n\n"
                    f"**Before**\n{before_content}\n\n"
                    f"**After**\n{after_content}\n\n",
                    discord.Color.dark_blue(),
                    before.author
                )
                await channel.send(embed=embed)

    # --- Channel created ---
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if isinstance(channel, discord.TextChannel):
            log_channel = self.get_log_channel(channel.guild)
            if log_channel:
                embed = self.create_embed("📗 Channel Created", f"Text channel created: {channel.mention}")
                await log_channel.send(embed=embed)

    # --- Channel deleted ---
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if isinstance(channel, discord.TextChannel):
            log_channel = self.get_log_channel(channel.guild)
            if log_channel:
                embed = self.create_embed("📕 Channel Deleted", f"Text channel deleted: **#{channel.name}**")
                await log_channel.send(embed=embed)

    # --- Channel name update ---
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if isinstance(before, discord.TextChannel) and before.name != after.name:
            log_channel = self.get_log_channel(before.guild)
            if log_channel:
                embed = self.create_embed("📝 Channel Renamed",
                    f"**Before:** #{before.name}\n**After:** #{after.name}", discord.Color.teal())
                await log_channel.send(embed=embed)

    # --- Role created ---
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        channel = self.get_log_channel(role.guild)
        if channel:
            embed = self.create_embed("➕ Role Created", f"New role created: **{role.name}**", discord.Color.green())
            await channel.send(embed=embed)

    # --- Role deleted ---
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        channel = self.get_log_channel(role.guild)
        if channel:
            embed = self.create_embed("➖ Role Deleted", f"Role deleted: **{role.name}**", discord.Color.red())
            await channel.send(embed=embed)

    # --- Role updated ---
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        channel = self.get_log_channel(after.guild)
        if not channel:
            return

        changes = []

        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")

        if before.color != after.color:
            changes.append(f"**Farbe:** `{before.color}` → `{after.color}`")

        if before.permissions != after.permissions:
            changes.append("**Berechtigungen wurden geändert**")

        if before.hoist != after.hoist:
            changes.append(f"**Separat anzeigen:** `{before.hoist}` → `{after.hoist}`")

        if before.mentionable != after.mentionable:
            changes.append(f"**Erwähnbar:** `{before.mentionable}` → `{after.mentionable}`")

        if changes:
            embed = self.create_embed("🛠️ Role Updated",
                f"**Rolle:** {after.mention}\n\n" + "\n".join(changes),
                discord.Color.orange())
            await channel.send(embed=embed)


    # --- Server updated ---
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        channel = self.get_log_channel(after)
        if channel and before.name != after.name:
            embed = self.create_embed("🏷️ Server Renamed",
                f"**Before:** {before.name}\n**After:** {after.name}", discord.Color.purple())
            await channel.send(embed=embed)

    # --- Member updated (nickname, roles) ---
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        channel = self.get_log_channel(after.guild)
        if not channel:
            return

        changes = []

        if before.nick != after.nick:
            changes.append(f"**Nickname changed:** `{before.nick}` → `{after.nick}`")

        added_roles = [r for r in after.roles if r not in before.roles]
        removed_roles = [r for r in before.roles if r not in after.roles]

        if added_roles:
            changes.append(f"**Roles added:** {', '.join(r.mention for r in added_roles)}")
        if removed_roles:
            changes.append(f"**Roles removed:** {', '.join(r.mention for r in removed_roles)}")

        if changes:
            embed = self.create_embed("🔁 Member Updated", "\n".join(changes), discord.Color.blurple(), after)
            await channel.send(embed=embed)


    # --- Member banned ---
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        channel = self.get_log_channel(guild)
        if channel:
            embed = self.create_embed("🔨 Member Banned", f"{user.mention} was banned.", discord.Color.dark_red(), user)
            await channel.send(embed=embed)

    # --- Member unbanned ---
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        channel = self.get_log_channel(guild)
        if channel:
            embed = self.create_embed("✅ Member Unbanned", f"{user.mention} was unbanned.", discord.Color.green(), user)
            await channel.send(embed=embed)

    # Warn / Unwarn
    async def log_warn(self, guild, moderator, user, reason="No reason provided."):
        channel = self.get_log_channel(guild)
        if channel:
            embed = self.create_embed("⚠️ Member Warned", f"**{user.mention}** was warned by **{moderator.mention}**\n**Reason:** {reason}", discord.Color.orange(), user)
            await channel.send(embed=embed)

    async def log_unwarn(self, guild, moderator, user):
        channel = self.get_log_channel(guild)
        if channel:
            embed = self.create_embed("✅ Warn Removed", f"**{user.mention}** had a warning removed by **{moderator.mention}**", discord.Color.green(), user)
            await channel.send(embed=embed)
            
    # Lock / Unlock
    async def log_action(self, guild: discord.Guild, embed: discord.Embed):
        channel = self.get_log_channel(guild)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LoggingCog(bot))
