import discord
from discord.ext import commands
import json
import os

class Cleaner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 📁 ARQUIVO DE CONFIG
        self.file = "config.json"

        # cria o arquivo se não existir
        if not os.path.exists(self.file):
            with open(self.file, "w") as f:
                json.dump({"cleaner_channels": []}, f, indent=4)

        # carrega dados
        with open(self.file, "r") as f:
            data = json.load(f)

        self.canais_permitidos = data.get("cleaner_channels", [])
        
        # 🔗 LINKS AUTORIZADOS
        self.links_autorizados = [
            "mega.nz",
            "drive.google.com",
            "tiktok.com",
            "streamable.com",
            "cdn.nsb.gg"
        ]

    # 💾 SALVAR NO CONFIG.JSON
    def salvar_canais(self):
        with open(self.file, "r") as f:
            data = json.load(f)

        data["cleaner_channels"] = self.canais_permitidos

        with open(self.file, "w") as f:
            json.dump(data, f, indent=4)

    # 📌 ADICIONAR CANAL
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setcleaner(self, ctx, canal: discord.TextChannel = None):
        canal = canal or ctx.channel
        canal_id = canal.id

        if canal_id in self.canais_permitidos:
            return await ctx.send("❌ Esse canal já está configurado.")

        self.canais_permitidos.append(canal_id)
        self.salvar_canais()

        await ctx.send(f"✅ Canal {canal.mention} adicionado ao Cleaner.")

    # 🗑️ REMOVER CANAL
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removecleaner(self, ctx, canal: discord.TextChannel = None):
        canal = canal or ctx.channel
        canal_id = canal.id

        if canal_id not in self.canais_permitidos:
            return await ctx.send("❌ Esse canal não está configurado.")

        self.canais_permitidos.remove(canal_id)
        self.salvar_canais()

        await ctx.send(f"🗑️ Canal {canal.mention} removido.")

    # 🔍 VERIFICAR LINK
    def link_permitido(self, conteudo: str) -> bool:
        conteudo = conteudo.lower()

        if "discord.gg" in conteudo or "discord.com/invite" in conteudo:
            return False

        if "http://" in conteudo or "https://" in conteudo:
            return any(link in conteudo for link in self.links_autorizados)

        return False

    # 📎 VERIFICAR ANEXO
    def apenas_anexo(self, message: discord.Message) -> bool:
        return len(message.attachments) > 0

    # 🧹 EVENTO PRINCIPAL
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
                    print(f"⚠️ Sem permissão no canal {message.channel.name}")
                except discord.HTTPException as e:
                    print(f"⚠️ Erro ao deletar: {e}")

async def setup(bot):
    await bot.add_cog(Cleaner(bot))
