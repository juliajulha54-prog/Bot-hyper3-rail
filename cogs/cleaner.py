import discord
from discord.ext import commands
import json
import os

CONFIG_FILE = "config.json"

# ---------------- JSON (NÃO REMOVIDO) ----------------

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"canais_permitidos": []}, f)

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- DB (NOVO) ----------------

async def get_cleaner(bot, guild_id):
    return bot.db["cleaner"].find_one({"guild_id": str(guild_id)})

async def set_cleaner_db(bot, guild_id, data):
    bot.db["cleaner"].update_one(
        {"guild_id": str(guild_id)},
        {"$set": data},
        upsert=True
    )

# ---------------- COG ----------------

class Cleaner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        data = load_config()
        self.canais_permitidos = data.get("canais_permitidos", [])

        # 🔗 LINKS AUTORIZADOS
        self.links_autorizados = [
            "mega.nz",
            "drive.google.com",
            "tiktok.com",
            "streamable.com",
            "cdn.nsb.gg",
            "mediafire.com",
            "alight.link",
            "dropbox.com",
            "we.tl",
            "aftereffects",
            "adobe.com"
        ]

    # 🔥 CARREGAR DO DB AO INICIAR
    async def cog_load(self):
        for guild in self.bot.guilds:
            cfg = await get_cleaner(self.bot, guild.id)
            if cfg:
                self.canais_permitidos = cfg.get("canais_permitidos", [])

    def link_permitido(self, conteudo: str) -> bool:
        conteudo = conteudo.lower()

        if "discord.gg" in conteudo or "discord.com/invite" in conteudo:
            return False

        if "http://" in conteudo or "https://" in conteudo:
            return any(link in conteudo for link in self.links_autorizados)

        return False

    def apenas_anexo(self, message: discord.Message) -> bool:
        return len(message.attachments) > 0

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.channel.id in self.canais_permitidos:
            
            permitido = self.apenas_anexo(message) or self.link_permitido(message.content)

            if not permitido:
                try:
                    await message.delete()
                except discord.Forbidden:
                    print(f"⚠️ Sem permissão no canal {message.channel.id}")
                except discord.HTTPException as e:
                    print(f"⚠️ Erro ao deletar: {e}")

    # ---------------- COMANDOS ----------------

    @commands.command(name="setcleaner")
    @commands.has_permissions(administrator=True)
    async def set_cleaner(self, ctx, canal: discord.TextChannel):
        data = load_config()

        if canal.id not in data["canais_permitidos"]:
            data["canais_permitidos"].append(canal.id)
            save_config(data)

        self.canais_permitidos = data["canais_permitidos"]

        # 🔥 SALVA NO DB
        await set_cleaner_db(self.bot, ctx.guild.id, {
            "canais_permitidos": self.canais_permitidos
        })

        await ctx.reply(f"✅ Canal {canal.mention} configurado para o Cleaner.")

    @commands.command(name="removecleaner")
    @commands.has_permissions(administrator=True)
    async def remove_cleaner(self, ctx, canal: discord.TextChannel):
        data = load_config()

        if canal.id in data["canais_permitidos"]:
            data["canais_permitidos"].remove(canal.id)
            save_config(data)

        self.canais_permitidos = data["canais_permitidos"]

        # 🔥 ATUALIZA DB
        await set_cleaner_db(self.bot, ctx.guild.id, {
            "canais_permitidos": self.canais_permitidos
        })

        await ctx.reply(f"❌ Canal {canal.mention} removido do Cleaner.")


async def setup(bot):
    await bot.add_cog(Cleaner(bot))
