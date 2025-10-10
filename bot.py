from keep_alive import keep_alive
keep_alive()

import discord
from discord.ext import commands, tasks
from discord import app_commands
from supabase import acreate_client
import string
import os
from datetime import timedelta, datetime, timezone
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
supabase = None

ALLOWED_CHARS = set('e' + string.whitespace) | {',', '.', '!', '?'}
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

async def render(punishment, reason, expires):
    return f"""Hello,
you have been {punishment} in the \"Epic E Enforcement\" server.
Reason: {reason}
Expires: {'<t:'+str(expires)+':R>' if expires else ""}
Punishments may take a few minutes to be fully removed.
"""

@tasks.loop(seconds=30)
async def check_warns():
    global supabase
    now = datetime.now(timezone.utc).isoformat()
    expired = await supabase.table("warns").select("*").lt("expires", now).execute()

    if expired.data:
        ids = [row["id"] for row in expired.data]
        await supabase.table("warns").delete().in_("id", ids).execute()

@check_warns.before_loop
async def before_check_warns():
    await bot.wait_until_ready()

@tasks.loop(seconds=30)
async def check_mutes(): # this function made me lose my sanity
    global supabase
    now = datetime.now(timezone.utc).isoformat()

    expired = await supabase.table("mutes").select("*").lt("expires", now).execute()
    if not expired.data:
        return

    user_ids = [row["user_id"] for row in expired.data]
    mute_ids = [row["id"] for row in expired.data]

    await supabase.table("mutes").delete().in_("id", mute_ids).execute()

    guild = bot.get_guild(1425229583103561781)
    role = discord.utils.get(guild.roles, name="Muted")

    members = []
    for user_id in user_ids:
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                continue
        members.append(member)

        if members:
            await asyncio.gather(*(member.remove_roles(role) for member in members))

@check_mutes.before_loop
async def before_check_mutes():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    global supabase
    await bot.tree.sync()
    supabase = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
    check_warns.start()
    check_mutes.start()

async def enforce_e_only(message: discord.Message):
    """Delete messages that break the E-only rule."""
    if not message.guild:
        return
    if message.author.bot:
        return
    content = set(message.content.lower())
    role_names = [role.name for role in message.author.roles]
    if (not content.issubset(ALLOWED_CHARS) or message.attachments) and "Exempt" not in role_names:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, messages must consist only of allowed characters (e, whitespace, punctuation).", delete_after=5)
        except discord.errors.NotFound:
            pass

@bot.event
async def on_message(message: discord.Message):
    await enforce_e_only(message)

@bot.tree.command(name="exempt", description="Exempt a member.")
async def exempt(interaction: discord.Interaction, member: discord.Member):
    exempt_role = discord.utils.get(interaction.guild.roles, name="Exempt")
    staff_role = discord.utils.get(interaction.guild.roles, name="Staff")
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message('You need Staff to exempt members.', ephemeral=True)
        return
    if exempt_role in member.roles:
        await interaction.response.send_message('That member is already exempted.', ephemeral=True)
        return
    await member.add_roles(exempt_role)
    await interaction.response.send_message(f"Exempted {member.mention}.")

@bot.tree.command(name="de-exempt", description="De-exempt a member.")
async def de_exempt(interaction: discord.Interaction, member: discord.Member):
    exempt_role = discord.utils.get(interaction.guild.roles, name="Exempt")
    staff_role = discord.utils.get(interaction.guild.roles, name="Staff")
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message('You need Staff to de-exempt members.', ephemeral=True)
        return
    if exempt_role not in member.roles:
        await interaction.response.send_message('That member isn\'t exempted.', ephemeral=True)
        return
    if interaction.user == member:
        await interaction.response.send_message('You probably don\'t want to de-exempt yourself.', ephemeral=True)
        return
    if interaction.user.top_role <= member.top_role:
        await interaction.response.send_message('That member is higher or at the same level as you in the role hierarchy.', ephemeral=True)
        return
    await member.remove_roles(exempt_role)
    await interaction.response.send_message(f"De-exempted {member.mention}.")

@bot.tree.command(name="warn", description="Warn a member.")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    global supabase
    expires = datetime.now(timezone.utc) + timedelta(days=30)
    staff_role = discord.utils.get(interaction.guild.roles, name="Staff")
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("You need Staff to warn members.", ephemeral=True)
        return
    if staff_role in member.roles:
        await interaction.response.send_message("You cannot warn Staff.", ephemeral=True)
        return
    rendered_message = await render("warned", reason, int(expires.timestamp()))
    try:
        await member.send(rendered_message)
    except discord.Forbidden:
        pass
    await interaction.response.send_message(f"{member.mention} warned.")
    await supabase.table("warns").insert({
        "user_id": member.id,
        "expires": expires.isoformat(),
        "reason": reason
    }).execute()

@bot.tree.command(name="mute", description="Mute a member.")
async def mute(interaction: discord.Interaction, member: discord.Member, reason: str, duration: int):
    global supabase
    expires = datetime.now(timezone.utc) + timedelta(seconds=duration)
    staff_role = discord.utils.get(interaction.guild.roles, name="Staff")
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("You need Staff to mute members.", ephemeral=True)
        return
    if staff_role in member.roles:
        await interaction.response.send_message("You cannot mute Staff.", ephemeral=True)
        return
    rendered_message = await render("muted", reason, int(expires.timestamp()))
    try:
        await member.send(rendered_message)
    except discord.Forbidden:
        pass
    await member.add_roles(discord.utils.get(interaction.guild.roles, name="Muted"))
    await interaction.response.send_message(f"{member.mention} muted.")
    await supabase.table("mutes").insert({
        "user_id": member.id,
        "expires": expires.isoformat(),
        "reason": reason
    }).execute()

@bot.tree.command(name="unmute", description="Unmute a member.")
async def unmute(interaction: discord.Interaction, member: discord.Member, reason: str):
    global supabase
    staff_role = discord.utils.get(interaction.guild.roles, name="Staff")
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("You need Staff to unmute members.", ephemeral=True)
        return
    if muted_role not in member.roles:
        await interaction.response.send_message("That member is not muted.", ephemeral=True)
        return
    rendered_message = await render("unmuted", reason, None)
    try:
        await member.send(rendered_message)
    except discord.Forbidden:
        pass
    await member.remove_roles(muted_role)
    await interaction.response.send_message(f"{member.mention} unmuted.")
    await supabase.table("mutes").delete().eq("user_id", member.id).execute()

@bot.tree.error
async def all_commands_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.TransformerError):
        await interaction.response.send_message("You need to be in a guild to use this command.", ephemeral=True)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    await enforce_e_only(after)

bot.run(os.getenv("BOT_TOKEN"))