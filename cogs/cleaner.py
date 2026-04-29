import discord
from discord.ext import commands
import re
import json

# ---------------- LOAD CONFIG ---------------- #

with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

CANAIS_PERMITIDOS = CONFIG.get("canais_permitidos", [])
LINKS_PERMITIDOS = CONFIG.get("links_permitidos", [])

link_regex = re.compile(r"https?://")

# ---------------- COG ---------------- #

class Cleaner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def link_valido(self, content):
        content = content.lower()

        if "discord.gg" in content or "discord.com/invite" in content:
            return False

        if link_regex.search(content):
            return any(link in content for link in LINKS_PERMITIDOS)

        return False

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not m.guild or m.author.bot:
            return

        # ignora staff
        if m.author.guild_permissions.manage_messages:
            return

        # só roda nos canais configurados
        if m.channel.id not in CANAIS_PERMITIDOS:
            return

        content = m.content.strip()

        has_attachment = len(m.attachments) > 0
        has_link = self.link_valido(content)
        has_sticker = len(m.stickers) > 0

        # ❌ texto puro / emoji
        if not has_attachment and not has_link:
            try:
                await m.delete()
            except:
                pass
            return

        # ❌ figurinha
        if has_sticker:
            try:
                await m.delete()
            except:
                pass
            return

        await self.bot.process_commands(m)

# ---------------- SETUP ---------------- #

async def setup(bot):
    await bot.add_cog(Cleaner(bot))
