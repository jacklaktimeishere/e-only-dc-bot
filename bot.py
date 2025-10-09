from keep_alive import keep_alive
keep_alive()

import discord
from discord.ext import commands
from discord import app_commands
import string
import os

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

ALLOWED_CHARS = set('e' + string.whitespace) | {',', '.', '!', '?'}

@bot.event
async def on_ready():
    await bot.tree.sync()

async def enforce_e_only(message: discord.Message):
    """Delete messages that break the E-only rule."""
    if message.author.bot:
        return
    content = set(message.content.lower())
    role_names = [role.name for role in message.author.roles]
    if not content.issubset(ALLOWED_CHARS) and "Exempt" not in role_names:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, messages must consist only of allowed characters (e, whitespace, punctuation).", delete_after=5)
        except discord.errors.NotFound:
            pass

@bot.event
async def on_message(message: discord.Message):
    await enforce_e_only(message)

@bot.tree.command(name="exempt")
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

@bot.tree.command(name="de-exempt")
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

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    await enforce_e_only(after)

bot.run(os.getenv("BOT_TOKEN"))