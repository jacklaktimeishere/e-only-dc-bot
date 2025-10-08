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

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    await enforce_rules(after)

bot.run(os.getenv("BOT_TOKEN"))