from discord import Role, Member, Embed, Color, app_commands
import discord
import asyncio
import json
import pyfiglet
from discord.ext import commands, tasks
import random
import itertools
import os
from datetime import datetime, UTC, timedelta

# Bot configuration
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.guilds = True

# Bot Setup
# Load bot configuration
with open("config.json") as config_file:
    config = json.load(config_file)

current_prefix = "?"

# Bot instance with dynamic prefix
def get_prefix(bot, message):
    return current_prefix

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

# Maximale Verwarnungsstufen
WARNING_ACTIONS = {
    1: "timeout_10m",     # for 1 Warnings: Timeout 10 Minutes
    2: "",                # for 2 Warnings: Nothing
    3: "timeout_1_6h",    # for 3 Warnings: Timeout 1-6 hours
    4: "timeout_24_72h",  # for 4 Warnings: Timeout 24-72 hours
    5: "kick",            # for 5 Warnings: Kick
    6: "ban"              # for 6 Warnings: Ban
}

WARN_FILE = "warnings.json"
COOLDOWN_HOURS = 5
COOLDOWN_FILE = "revive_cooldowns.json"

# Liste der Aktivitäten
activity_types = itertools.cycle([
    discord.Activity(type=discord.ActivityType.playing, name="Oceanic City´s Security"),  # Playing
    discord.Activity(type=discord.ActivityType.watching, name="over Oceanic City"),  # Watching
])

@bot.event
async def on_ready():
    ascii_banner = pyfiglet.figlet_format("Oceanic City Security", font="slant")
    print(ascii_banner)

    # Versuch, die Logging-Erweiterung zu laden
    try:
        await bot.load_extension("logging_cog")  # Dateiname ohne .py
        print("✅ LoggingCog geladen.")
    except Exception as e:
        print(f"Fehler beim Laden von LoggingCog: {e}")

    # Slash-Commands synchronisieren
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} Slash-Commands synchronisiert.")
    except Exception as e:
        print(f"❌ Fehler beim Synchronisieren der Slash-Commands: {e}")
        
   # Starte die wiederkehrende Task, um den Status zu ändern
    change_status.start()

@tasks.loop(minutes=15)  # Alle 15 Minuten
async def change_status():
    activity = next(activity_types)  # Hole die nächste Aktivität aus der Liste
    await bot.change_presence(
        activity=activity,
        status=discord.Status.online  # Setze den Status auf 'online', 'idle', 'dnd', oder 'invisible'
    )
    
async def mute_member(ctx_or_interaction, member: discord.Member, is_interaction=False):
    """
    Gemeinsame Logik für das Stummschalten eines Mitglieds.
    """
    mute_role = discord.utils.get(member.guild.roles, name="Muted 🔇")

    if not mute_role:
        embed = discord.Embed(
            title="Error",
            description="The 'Muted' role does not exist. Please create it first.",
            color=discord.Color.red()
        )
        if is_interaction:
            await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)
        return

    if member.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Error",
            description="You cannot mute staff members.",
            color=discord.Color.red()
        )
        if is_interaction:
            await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)
        return

    try:
        await member.add_roles(mute_role)
        embed = discord.Embed(
            title="User Muted",
            description=f"{member.mention} has been muted.",
            color=discord.Color.purple()
        )
        if is_interaction:
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Could not mute {member.mention}.\nError: {e}",
            color=discord.Color.red()
        )
        if is_interaction:
            await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)

def load_warnings():
    if os.path.exists(WARN_FILE):
        with open(WARN_FILE, "r") as f:
            return {int(k): v for k, v in json.load(f).items()}
    return {}

def save_warnings():
    with open(WARN_FILE, "w") as f:
        json.dump({str(k): v for k, v in warns.items()}, f, indent=4)

warns = load_warnings()            
            
# Helper function to create an embed
def create_embed(title, description, color=discord.Color.blue()):
    """Helper function to create embeds."""
    return discord.Embed(title=title, description=description, color=color)

# Load cooldown data
if os.path.exists(COOLDOWN_FILE):
    with open(COOLDOWN_FILE, "r") as f:
        last_revive_ping = json.load(f)
        last_revive_ping = {
    int(k): datetime.fromisoformat(v).replace(tzinfo=UTC)
    for k, v in last_revive_ping.items()
}
else:
    last_revive_ping = {}

def save_cooldowns():
    with open(COOLDOWN_FILE, "w") as f:
        json.dump({str(k): v.isoformat() for k, v in last_revive_ping.items()}, f)

def get_cooldown_remaining(guild_id):
    now = datetime.now(UTC)
    if guild_id in last_revive_ping:
        elapsed = now - last_revive_ping[guild_id]
        if elapsed < timedelta(hours=COOLDOWN_HOURS):
            return timedelta(hours=COOLDOWN_HOURS) - elapsed
    return None

def get_general_channel(guild: discord.Guild):
    for channel in guild.text_channels:
        if channel.name.lower() == "🐟・general":
            return channel
    return None

# Revive Command
@bot.command(name="revive")
@commands.has_permissions(kick_members=True)
async def revive_command(ctx):
    """
    Send a chat revive ping (Admin only)
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    general_channel = get_general_channel(ctx.guild)
    if not general_channel:
        await ctx.send("No channel named `🐟・general` was found.")
        return

    remaining = get_cooldown_remaining(ctx.guild.id)
    if remaining:
        hours, rem = divmod(remaining.total_seconds(), 3600)
        minutes, _ = divmod(rem, 60)
        await ctx.send(f"The revive ping is on cooldown! Try again in **{int(hours)}h {int(minutes)}m**.")
        return

    await general_channel.send("<@&1317781926752424006> Let's bring this chat back to life!")
    last_revive_ping[ctx.guild.id] = datetime.now(UTC)
    save_cooldowns()
    await ctx.send(f"Revive ping sent to {general_channel.mention}!")

# Revive Command
@bot.tree.command(name="revive", description="Send a chat revive ping (Admin only)")
async def revive_slash(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("You need to have Kick Members permission to use this command.", ephemeral=True)
        return

    general_channel = get_general_channel(interaction.guild)
    if not general_channel:
        await interaction.response.send_message("No channel named `general` was found.", ephemeral=True)
        return

    remaining = get_cooldown_remaining(interaction.guild.id)
    if remaining:
        hours, rem = divmod(remaining.total_seconds(), 3600)
        minutes, _ = divmod(rem, 60)
        await interaction.response.send_message(
            f"The revive ping is on cooldown! Try again in **{int(hours)}h {int(minutes)}m**.",
            ephemeral=True
        )
        return

    await general_channel.send("<@&1317781926752424006> Let's bring this chat back to life!")
    last_revive_ping[interaction.guild.id] = datetime.now(UTC)
    save_cooldowns()
    await interaction.response.send_message(
        f"Revive ping sent to {general_channel.mention}!", ephemeral=True
    )

# Ping Command
@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)  # Latenz in Millisekunden
    await ctx.send(f"🏓 Pong! Bot Latency: `{latency}ms`")

# Ping Command
@bot.tree.command(name="ping", description="Check the bot's latency.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)  # Latenz in Millisekunden
    await interaction.response.send_message(f"🏓 Pong! Bot Latency: `{latency}ms`")

# List for all Commands
@bot.command(name="help")
@commands.has_permissions(kick_members=True)
async def help_command(ctx):
    """
    Sends an embedded list of all prefix-based commands for the bot.
    """
    # Holen des tatsächlichen Prefix-Werts
    prefixes = await bot.get_prefix(ctx.message)  # Abrufen der Prefixe
    if isinstance(prefixes, list):
        prefix = prefixes[0]  # Den ersten Prefix verwenden
    else:
        prefix = prefixes

    commands = list(bot.commands)  # Konvertiere das Set in eine Liste
    embed_list = []

    # Chunk commands into groups of 25
    for i in range(0, len(commands), 25):
        chunk = commands[i:i + 25]
        embed = discord.Embed(
            title="📜 Bot Help",
            description="Here's a list of all available commands.",
            color=discord.Color.blue()
        )
        for command in chunk:
            embed.add_field(
                name=f"`{prefix}{command.name}`",  # Verwende den tatsächlichen Prefix
                value=command.help or "No description provided.",
                inline=False
            )
        embed.set_footer(text="Use the command prefix followed by the command name to execute.")
        embed_list.append(embed)

    for embed in embed_list:
        await ctx.send(embed=embed)


# Help for Slash Commands
@bot.tree.command(name="help")
@app_commands.checks.has_permissions(kick_members=True)
async def slash_help(interaction: discord.Interaction):
    """
    Sends an embedded list of all slash commands for the bot.
    """
    embed = discord.Embed(
        title="📜 Bot Slash Commands",
        description="Here's a list of all available slash commands.",
        color=discord.Color.green()
    )
    
    # Access all registered slash commands
    commands = bot.tree.get_commands()
    for command in commands:
        embed.add_field(
            name=f"/{command.name}",
            value=command.description or "No description provided.",
            inline=False
        )
    
    embed.set_footer(text="Use a slash (`/`) followed by the command name to execute.")
    await interaction.response.send_message(embed=embed, ephemeral=False)


# Command: Show or change the prefix
@bot.command()
async def prefix(ctx, new_prefix: str = None):
    """
    Shows the current prefix or changes it if a new one is provided.
    """
    global current_prefix

    if new_prefix is None:
        embed = create_embed("Current Prefix", f"The current prefix is `{current_prefix}`.")
        await ctx.send(embed=embed)
        return

    # Check if the user has administrator permissions
    if not ctx.author.guild_permissions.administrator:
        embed = create_embed("Permission Error", "Only administrators can change the prefix.", discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Change the prefix if the user is an administrator
    current_prefix = new_prefix
    embed = create_embed("Prefix Changed", f"The prefix has been successfully changed to `{current_prefix}`.", discord.Color.green())
    await ctx.send(embed=embed)

# Slash command to show or change the prefix
@bot.tree.command(name="prefix", description="Shows the current prefix or changes it if a new one is provided.")
@app_commands.checks.has_permissions(administrator=True)
async def slash_prefix(interaction: discord.Interaction, new_prefix: str = None):
    """
    Shows the current prefix or changes it if a new one is provided through slash commands.
    """
    global current_prefix

    if new_prefix is None:
        embed = create_embed("Current Prefix", f"The current prefix is `{current_prefix}`.")
        await interaction.response.send_message(embed=embed)
        return

    # Change the prefix if the user is an administrator
    current_prefix = new_prefix
    embed = create_embed("Prefix Changed", f"The prefix has been successfully changed to `{current_prefix}`.", discord.Color.green())
    await interaction.response.send_message(embed=embed)

@slash_prefix.error
async def slash_prefix_error(interaction: discord.Interaction, error):
    """
    Error handling for the slash prefix command.
    """
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = create_embed("Permission Error", "You do not have the required permissions to change the prefix.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = create_embed("Error", "An unexpected error occurred.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Purge command with error handling for message deletion
@bot.command()
@commands.has_permissions(administrator=True)
async def purge(ctx, amount: int = None):
    """
    Purge a number of messages from the channel.
    If no amount is specified, an embed with usage instructions will be sent.
    """
    # If no amount is specified, send an embed with usage instructions
    if amount is None:
        embed = discord.Embed(
            title=f"🧹 Purge Command 🧹",
            description=(f"Usage: `{ctx.prefix}purge <number>`\n\n"
                         "This command allows administrators to delete a specified number of messages from the channel. "
                         "The amount parameter is the number of messages to delete. The command will also delete the command message itself."),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Only users with 'Administrator' permission can use this command.")
        await ctx.send(embed=embed, delete_after=10)
        return

    try:
        await ctx.channel.purge(limit=amount + 1)  # +1 to delete the command message as well
        embed = discord.Embed(
            title="🧹 Messages Purged 🧹",
            description=f"{amount} messages have been deleted.",
            color=discord.Color.green()  # Green text for success
        )
        await ctx.send(embed=embed, delete_after=5)
    except Exception as e:
        embed = discord.Embed(
            title="⚠️ Error ⚠️",
            description=f"Could not purge messages.\nError: {e}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=10)

    # Attempt to delete the command message if it still exists
    try:
        await ctx.message.delete()  # Deletes the message that triggered the command
    except discord.errors.NotFound:
        pass  # The message no longer exists, so we ignore the error

# Slash command version for purging messages
@bot.tree.command(name="purge", description="Purge a number of messages from the channel.")
@app_commands.checks.has_permissions(administrator=True)
async def slash_purge(interaction: discord.Interaction, amount: int = None):
    """
    Purge a number of messages from the channel using slash commands.
    """
    if amount is None:
        embed = discord.Embed(
            title=f"🧹 Purge Command 🧹",
            description=(f"Usage: /purge <number>\n\n"
                         "This command allows administrators to delete a specified number of messages from the channel. "
                         "The amount parameter is the number of messages to delete. The command will also delete the command message itself."),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Only users with 'Administrator' permission can use this command.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        # Defer the response so the interaction does not time out
        await interaction.response.defer()
    
        await interaction.channel.purge(limit=amount + 1)  # +1 to delete the command message as well
        
    except Exception as e:
        # Fehlerbehandlung ohne eine Bestätigung an den Nutzer
        pass

# Ban command
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member = None, *, reason="No reason provided"):
    """
    Ban a member from the server.
    """
    if not member:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To ban a user, use the command as follows:\n`{ctx.prefix}ban <member> [reason]`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="User Banned",
            description=f"{member.name} has been banned.\nReason: {reason}",
            color=discord.Color.red()  # Red text for banning
        )
        message = await ctx.send(embed=embed)
        await ctx.message.delete()  # Deletes the message that triggered the command
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Could not ban {member.name}.\nError: {e}",
            color=discord.Color.red()
        )
        message = await ctx.send(embed=embed)
        await ctx.message.delete()  # Deletes the message that triggered the command

# Slash command version for banning members
@bot.tree.command(name="ban", description="Ban a member from the server.")
@app_commands.checks.has_permissions(ban_members=True)
async def slash_ban(interaction: discord.Interaction, member: discord.Member = None, reason: str = "No reason provided"):
    """
    Ban a member from the server using slash commands.
    """
    if not member:
        embed = discord.Embed(
            title="Usage Instructions",
            description="To ban a user, use the command as follows:\n`/ban <member> [reason]`",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="User Banned",
            description=f"{member.name} has been banned.\nReason: {reason}",
            color=discord.Color.red()  # Red text for banning
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Could not ban {member.name}.\nError: {e}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Unban command
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user: discord.User = None, *, reason="No reason provided"):
    """
    Unban a member from the server.
    """
    if not user:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To unban a user, use the command as follows:\n`{ctx.prefix}unban <user> [reason]`\n\n"
                        "**<user>**: The user you want to unban (mention or username).\n"
                        "**[reason]**: Optional reason for unbanning.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    try:
        await ctx.guild.unban(user, reason=reason)
        embed = discord.Embed(
            title="User Unbanned",
            description=f"{user.name} has been unbanned.\nReason: {reason}",
            color=discord.Color.green()  # Green text for success
        )
        message = await ctx.send(embed=embed)
        await ctx.message.delete()  # Deletes the message that triggered the command
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Could not unban {user.name}.\nError: {e}",
            color=discord.Color.red()
        )
        message = await ctx.send(embed=embed)
        await ctx.message.delete()  # Deletes the message that triggered the command

# Slash command version for unbanning users
@bot.tree.command(name="unban", description="Unban a member from the server.")
@app_commands.checks.has_permissions(ban_members=True)
async def slash_unban(interaction: discord.Interaction, user: discord.User = None, reason: str = "No reason provided"):
    """
    Unban a member from the server using slash commands.
    """
    if not user:
        embed = discord.Embed(
            title="Usage Instructions",
            description="To unban a user, use the command as follows:\n`/unban <user> [reason]`\n\n"
                        "**<user>**: The user you want to unban (mention or username).\n"
                        "**[reason]**: Optional reason for unbanning.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await interaction.guild.unban(user, reason=reason)
        embed = discord.Embed(
            title="User Unbanned",
            description=f"{user.name} has been unbanned.\nReason: {reason}",
            color=discord.Color.green()  # Green text for success
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Could not unban {user.name}.\nError: {e}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Kick command
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member = None, *, reason="No reason provided"):
    """
    Kick a member from the server.
    """
    if not member:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To kick a user, use the command as follows:\n`{ctx.prefix}kick <member> [reason]`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="User Kicked",
            description=f"{member.name} has been kicked.\nReason: {reason}",
            color=discord.Color.orange()  # Orange text for the action
        )
        message = await ctx.send(embed=embed)
        await ctx.message.delete()  # Deletes the message that triggered the command
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Could not kick {member.name}.\nError: {e}",
            color=discord.Color.red()
        )
        message = await ctx.send(embed=embed)
        await ctx.message.delete()  # Deletes the message that triggered the command

# Slash command version for kicking users
@bot.tree.command(name="kick", description="Kick a member from the server.")
@app_commands.checks.has_permissions(kick_members=True)
async def slash_kick(interaction: discord.Interaction, member: discord.Member = None, reason: str = "No reason provided"):
    """
    Kick a member from the server using slash commands.
    """
    if not member:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To kick a user, use the command as follows:\n`/kick <member> [reason]`",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="User Kicked",
            description=f"{member.name} has been kicked.\nReason: {reason}",
            color=discord.Color.orange()  # Orange text for the action
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Could not kick {member.name}.\nError: {e}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Warn command
@bot.command()
@commands.has_permissions(administrator=True)
async def warn(ctx, member: discord.Member = None, *, reason="No reason provided"):
    if not member:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"Usage: `{ctx.prefix}warn <member> [reason]`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    if member.guild_permissions.administrator:
        embed = create_embed("Permission Error", "You cannot warn staff members.", discord.Color.red())
        await ctx.send(embed=embed)
        return

    warns.setdefault(member.id, []).append(reason)
    save_warnings()
    warn_count = len(warns[member.id])

    embed = create_embed("User Warned", f"{member.mention} has been warned.\nReason: {reason}\nTotal Warnings: {warn_count}", discord.Color.orange())
    await ctx.send(embed=embed)

    cog = bot.get_cog("LoggingCog")
    if cog:
        await cog.log_warn(ctx.guild, ctx.author, member, reason)

    action = WARNING_ACTIONS.get(warn_count, "")
    now = datetime.now(UTC)
    try:
        if action == "timeout_10m":
            until = now + timedelta(minutes=10)
            await member.timeout(until, reason="1st warning")
            await ctx.send(f"{member.mention} was timed out for 10 minutes.")
        
        elif action == "timeout_1_6h":
            hours = random.randint(1, 6)
            until = now + timedelta(hours=hours)
            await member.timeout(until, reason="3rd warning")
            await ctx.send(f"{member.mention} was timed out for {hours} hours.")
        
        elif action == "timeout_24_72h":
            hours = random.randint(24, 72)
            until = now + timedelta(hours=hours)
            await member.timeout(until, reason="4th warning")
            await ctx.send(f"{member.mention} was timed out for {hours} hours.")

        elif action == "kick":
            await member.kick(reason="5th warning - Auto Kick")
            await ctx.send(f"{member.mention} has been kicked.")
            
        elif action == "ban":
            await member.ban(reason="6th warning - Auto Ban")
            await ctx.send(f"{member.mention} has been banned.")
    except Exception as e:
        await ctx.send(f"⚠️ Automatic action failed: `{e}`")

@bot.tree.command(name="warn", description="Warn a member for inappropriate behavior")
@discord.app_commands.checks.has_permissions(administrator=True)
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member.guild_permissions.administrator:
        embed = create_embed("Permission Error", "You cannot warn staff members.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    warns.setdefault(member.id, []).append(reason)
    save_warnings()
    warn_count = len(warns[member.id])

    embed = create_embed("User Warned", f"{member.mention} has been warned.\nReason: {reason}\nTotal Warnings: {warn_count}", discord.Color.orange())
    await interaction.response.send_message(embed=embed)

    cog = bot.get_cog("LoggingCog")
    if cog:
        await cog.log_warn(interaction.guild, interaction.user, member, reason)

    action = WARNING_ACTIONS.get(warn_count, "")
    now = datetime.now(UTC)
    try:
        if action == "timeout_10m":
            until = now + timedelta(minutes=10)
            await member.timeout(until, reason="1st warning")
            await ctx.send(f"{member.mention} was timed out for 10 minutes.")
        
        elif action == "timeout_1_6h":
            hours = random.randint(1, 6)
            until = now + timedelta(hours=hours)
            await member.timeout(until, reason="3rd warning")
            await ctx.send(f"{member.mention} was timed out for {hours} hours.")
        
        elif action == "timeout_24_72h":
            hours = random.randint(24, 72)
            until = now + timedelta(hours=hours)
            await member.timeout(until, reason="4th warning")
            await ctx.send(f"{member.mention} was timed out for {hours} hours.")

        elif action == "kick":
            await member.kick(reason="5th warning - Auto Kick")
            await ctx.send(f"{member.mention} has been kicked.")
            
        elif action == "ban":
            await member.ban(reason="6th warning - Auto Ban")
            await ctx.send(f"{member.mention} has been banned.")
    except Exception as e:
        await ctx.send(f"⚠️ Automatic action failed: `{e}`")

# Unwarn command
@bot.command()
@commands.has_permissions(administrator=True)  # Only administrators can execute this command
async def unwarn(ctx, member: discord.Member = None, warn_number: int = None):
    """
    Remove a specific warning from a member.
    """
    if not member or not warn_number:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To remove a warning, use the command as follows:\n`{ctx.prefix}unwarn <member> <warn_number>`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    if member.id in warns and len(warns[member.id]) >= warn_number:
        del warns[member.id][warn_number - 1]
        save_warnings()
        embed = create_embed("Warning Removed", f"Warning #{warn_number} has been removed from {member.name}.", discord.Color.green())  # Green for success
        await ctx.send(embed=embed)

        # Logging aufrufen – bei Erfolg!
        cog = bot.get_cog("LoggingCog")
        if cog:
            await cog.log_unwarn(ctx.guild, ctx.author, member)
    else:
        embed = create_embed("Error", f"Warning #{warn_number} not found for {member.name}.", discord.Color.red())  # Red for error
        await ctx.send(embed=embed)

# Slash command version
@bot.tree.command(name="unwarn")
@discord.app_commands.checks.has_permissions(administrator=True)  # Only administrators can execute this command
async def slash_unwarn(interaction: discord.Interaction, member: discord.Member = None, warn_number: int = None):
    """
    Remove a specific warning from a member via slash command.
    """
    if not member or not warn_number:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To remove a warning, use the command as follows:\n`/unwarn <member> <warn_number>`",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if member.id in warns and len(warns[member.id]) >= warn_number:
        del warns[member.id][warn_number - 1]
        save_warnings()
        embed = create_embed("Warning Removed", f"Warning #{warn_number} has been removed from {member.name}.", discord.Color.green())  # Green for success
        await interaction.response.send_message(embed=embed)

        # Logging aufrufen – bei Erfolg!
        cog = bot.get_cog("LoggingCog")
        if cog:
            await cog.log_unwarn(interaction.guild, interaction.user, member)
    else:
        embed = create_embed("Error", f"Warning #{warn_number} not found for {member.name}.", discord.Color.red())  # Red for error
        await interaction.response.send_message(embed=embed, ephemeral=True)

# View warnings command
@bot.command()
@commands.has_permissions(administrator=True)
async def warnings(ctx, member: discord.Member = None):
    if not member:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To view warnings of a user, use the command as follows:\n`{ctx.prefix}warnings <member>`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    user_warns = warns.get(member.id, [])
    if user_warns:
        warn_list = "\n".join([f"{idx+1}. {warn}" for idx, warn in enumerate(user_warns)])
        embed = create_embed("Warnings", f"{member.name} has the following warnings:\n{warn_list}", discord.Color.gold())
    else:
        embed = create_embed("Warnings", f"{member.name} has no warnings.", discord.Color.green())
    await ctx.send(embed=embed)

@bot.tree.command(name="warnings")
@discord.app_commands.checks.has_permissions(administrator=True)
async def slash_warnings(interaction: discord.Interaction, member: discord.Member = None):
    if not member:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To view warnings of a user, use the command as follows:\n`/warnings <member>`",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_warns = warns.get(member.id, [])
    if user_warns:
        warn_list = "\n".join([f"{idx+1}. {warn}" for idx, warn in enumerate(user_warns)])
        embed = create_embed("Warnings", f"{member.name} has the following warnings:\n{warn_list}", discord.Color.gold())
    else:
        embed = create_embed("Warnings", f"{member.name} has no warnings.", discord.Color.green())
    await interaction.response.send_message(embed=embed)

# Mute command
@bot.command(name="mute")
@commands.has_permissions(administrator=True)
async def prefix_mute(ctx, member: discord.Member = None):
    """
    Mute a member with a prefix-based command.
    """
    if not member:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To mute a user, use the command as follows:\n`{ctx.prefix}mute <member>`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    await mute_member(ctx, member)


# Slash-Command für Mute
@bot.tree.command(name="mute", description="Mute a member by assigning them the 'Muted' role.")
@app_commands.checks.has_permissions(administrator=True)
async def slash_mute(interaction: discord.Interaction, member: discord.Member):
    """
    Mute a member with a slash-based command.
    """
    await mute_member(interaction, member, is_interaction=True)


@slash_mute.error
async def slash_mute_error(interaction: discord.Interaction, error):
    """
    Fehlerbehandlung für den Slash-Command.
    """
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(
            title="Permission Error",
            description="You do not have the required permissions to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="Error",
            description="An unexpected error occurred.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)       
        

# Unmute command
@bot.command()
@commands.has_permissions(administrator=True)  # Only administrators can execute this command
async def unmute(ctx, member: discord.Member = None):
    """
    Unmute a member by removing the 'Muted' role.
    """
    if not member:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To unmute a user, use the command as follows:\n`{ctx.prefix}unmute <member>`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        embed = create_embed("Error", "The 'Muted' role does not exist.", discord.Color.red())
        await ctx.send(embed=embed)
        return

    try:
        await member.remove_roles(mute_role)
        embed = create_embed("User Unmuted", f"{member.name} has been unmuted.", discord.Color.green())  # Green for success
        await ctx.send(embed=embed)
    except Exception as e:
        embed = create_embed("Error", f"Could not unmute {member.name}.\nError: {e}", discord.Color.red())
        await ctx.send(embed=embed)

@bot.tree.command(name="unmute")
@discord.app_commands.checks.has_permissions(administrator=True)  # Only administrators can execute this command
async def slash_unmute(interaction: discord.Interaction, member: discord.Member = None):
    """
    Unmute a member by removing the 'Muted' role via slash command.
    """
    if not member:
        embed = discord.Embed(
            title="Usage Instructions",
            description=f"To unmute a user, use the command as follows:\n`/unmute <member>`",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not mute_role:
        embed = create_embed("Error", "The 'Muted' role does not exist.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await member.remove_roles(mute_role)
        embed = create_embed("User Unmuted", f"{member.name} has been unmuted.", discord.Color.green())  # Green for success
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        embed = create_embed("Error", f"Could not unmute {member.name}.\nError: {e}", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
# Role command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def role(ctx, member: discord.Member = None, role: discord.Role = None):
    """
    Toggle a role for a member.
    Usage:
    - role @member @role: Adds the role if the member doesn't have it, removes it otherwise.
    """
    # Überprüfen, ob die notwendigen Argumente bereitgestellt wurden
    if not member or not role:
        embed = discord.Embed(
            title="❌ Invalid Usage",
            description=(
                f"You need to specify a member and a role to use this command.\n\n"
                f"**Correct Usage:**\n"
                f"`{ctx.prefix}role @member @role`\n\n"
            ),
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Prüfen, ob der Benutzer die Rolle bereits hat
    if role in member.roles:
        # Rolle entfernen
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed the role **{role.name}** from {member.mention}.")
    else:
        # Rolle hinzufügen
        await member.add_roles(role)
        await ctx.send(f"✅ Added the role **{role.name}** to {member.mention}.")
        
        
@bot.tree.command()
async def role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    """
    Toggle a role for a member.
    Adds the role if the member doesn't have it, removes it otherwise.
    """
    # Berechtigungsprüfung: Überprüfen, ob der Benutzer die Berechtigung "Manage Roles" hat
    if not interaction.user.guild_permissions.manage_roles:
        embed = discord.Embed(
            title="❌ Permission Denied ❌",
            description="You do not have the required permission `Manage Roles` to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Check if the member already has the role
    if role in member.roles:
        # Remove the role
        await member.remove_roles(role)
        await interaction.response.send_message(f"✅ Removed the role **{role.name}** from {member.mention}.")
    else:
        # Add the role
        await member.add_roles(role)
        await interaction.response.send_message(f"✅ Added the role **{role.name}** to {member.mention}.")
        
# Lock command
@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock_command(ctx, *, reason="No reason provided"):
    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

    embed = discord.Embed(
        title="🔒 Channel Locked",
        description=f"{ctx.channel.mention} has been locked.\n📌 **Reason:** {reason}",
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Locked by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()

    await ctx.send(embed=embed)

    # Logging via LoggingCog
    logging_cog = ctx.bot.get_cog("LoggingCog")
    if logging_cog:
        log_embed = logging_cog.create_embed(
            "🔒 Channel Locked",
            f"{ctx.channel.mention} has been locked.\n**Reason:** {reason}",
            discord.Color.orange(),
            user=ctx.author
        )
        await logging_cog.log_action(ctx.guild, log_embed)
        
@bot.tree.command(name="lock", description="Locks the current channel for @everyone.")
@app_commands.describe(reason="Reason for locking")
@app_commands.checks.has_permissions(manage_channels=True)
async def slash_lock(interaction: discord.Interaction, reason: str = "No reason provided"):
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    embed = discord.Embed(
        title="🔒 Channel Locked",
        description=f"{interaction.channel.mention} has been locked.\n📌 **Reason:** {reason}",
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Locked by {interaction.user}", icon_url=interaction.user.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed)

    # Logging via LoggingCog
    logging_cog = interaction.client.get_cog("LoggingCog")
    if logging_cog:
        log_embed = logging_cog.create_embed(
            "🔒 Channel Locked",
            f"{interaction.channel.mention} has been locked.\n**Reason:** {reason}",
            discord.Color.orange(),
            user=interaction.user
        )
        await logging_cog.log_action(interaction.guild, log_embed)
        
@lock_command.error
async def lock_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need `Manage Channels`, permission(s) to use that command.")

@slash_lock.error
async def slash_lock_error(interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need `Manage Channels`, permission(s) to use that command.", ephemeral=True)
        
# Unlock command
@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock_command(ctx, *, reason="No reason provided"):
    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = None  # Remove the lock
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

    embed = discord.Embed(
        title="🔓 Channel Unlocked",
        description=f"{ctx.channel.mention} has been unlocked.\n📌 **Reason:** {reason}",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Unlocked by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()

    await ctx.send(embed=embed)

    # Logging via LoggingCog
    logging_cog = ctx.bot.get_cog("LoggingCog")
    if logging_cog:
        log_embed = logging_cog.create_embed(
            "🔓 Channel Unlocked",
            f"{ctx.channel.mention} has been unlocked.\n**Reason:** {reason}",
            discord.Color.green(),
            user=ctx.author
        )
        await logging_cog.log_action(ctx.guild, log_embed)
        
@bot.tree.command(name="unlock", description="Unlocks the current channel for @everyone.")
@app_commands.describe(reason="Reason for unlocking")
@app_commands.checks.has_permissions(manage_channels=True)
async def slash_unlock(interaction: discord.Interaction, reason: str = "No reason provided"):
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    embed = discord.Embed(
        title="🔓 Channel Unlocked",
        description=f"{interaction.channel.mention} has been unlocked.\n📌 **Reason:** {reason}",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Unlocked by {interaction.user}", icon_url=interaction.user.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed)

    # Logging via LoggingCog
    logging_cog = interaction.client.get_cog("LoggingCog")
    if logging_cog:
        log_embed = logging_cog.create_embed(
            "🔓 Channel Unlocked",
            f"{interaction.channel.mention} has been unlocked.\n**Reason:** {reason}",
            discord.Color.green(),
            user=interaction.user
        )
        await logging_cog.log_action(interaction.guild, log_embed)
        
# Run the bot with your token
bot.run(config["token"])
