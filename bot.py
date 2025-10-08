from keep_alive import keep_alive
keep_alive()

import discord
from discord.ext import commands
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
    print(f"✅ Logged in as {bot.user}")

async def enforce_rules(message: discord.Message):
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
    await enforce_rules(message)
    await bot.process_commands(message)

@bot.command()
async def exempt(ctx, member: discord.Member):
    exempt_role = discord.utils.get(ctx.guild.roles, name="Exempt")
    staff_role = discord.utils.get(ctx.guild.roles, name="Staff")
    if staff_role not in ctx.author.roles:
        await ctx.send(f'{ctx.author.mention}, you need Staff to exempt members.', delete_after=5)
        return
    if exempt_role in member.roles:
        await ctx.send(f'{ctx.author.mention}, {member.mention} is already exempted.', delete_after=5)
        return
    await member.add_roles(exempt_role)
    await ctx.send(f"Exempted {member.mention}.")

@exempt.error
async def exempt_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(f"{ctx.author.mention}, that user is not in this server.", delete_after=5)

@bot.command()
async def de_exempt(ctx, member: discord.Member):
    exempt_role = discord.utils.get(ctx.guild.roles, name="Exempt")
    staff_role = discord.utils.get(ctx.guild.roles, name="Staff")
    if staff_role not in ctx.author.roles:
        await ctx.send(f'{ctx.author.mention}, you need Staff to de-exempt members.', delete_after=5)
        return
    if exempt_role not in member.roles:
        await ctx.send(f'{ctx.author.mention}, {member.mention} isn\'t exempted.', delete_after=5)
        return
    if ctx.author == member:
        await ctx.send(f'{ctx.author.mention}, you probably don\'t want to de-exempt yourself.', delete_after=5)
        return
    if ctx.author.top_role <= member.top_role:
        await ctx.send(f'{ctx.author.mention}, that member is higher or at the same level as you in the role hierarchy.', delete_after=5)
        return
    await member.remove_roles(exempt_role)
    await ctx.send(f"De-exempted {member.mention}.")

@de_exempt.error
async def de_exempt_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(f"{ctx.author.mention}, that user is not in this server.", delete_after=5)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    await enforce_rules(after)

bot.run(os.getenv("BOT_TOKEN"))