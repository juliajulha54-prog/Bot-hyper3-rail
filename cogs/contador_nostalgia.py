import discord
from discord.ext import commands
from pymongo import MongoClient

class ContadorNostalgia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Verifica se o bot tem o db
        if not hasattr(bot, "db"):
            raise ValueError("bot.db não encontrado. Certifique-se de definir bot.db antes de carregar o cog.")
        self.collection = bot.db["lock_backup"]

    def barra(self, atual, total):
        tamanho = 20
        progresso = int((atual / total) * tamanho) if total > 0 else 0
        return "█" * progresso + "░" * (tamanho - progresso)

    @commands.command(name="contadornostalgia")
    async def contadornostalgia(self, ctx):
        """Mostra o contador do modo nostalgia do LockSystem"""
        guild_id = ctx.guild.id
        data = self.collection.find_one({"guild_id": guild_id})

        if not data or "nostalgia" not in data:
            return await ctx.send("❌ | Nenhum contador de nostalgia encontrado para este servidor.")

        nostalgia = data["nostalgia"]
        msg_count = nostalgia.get("msg_count", 0)
        meta = nostalgia.get("meta_mensagens", 1800)
        lock_ativo = nostalgia.get("lock_ativo", False)

        barra = self.barra(msg_count, meta)
        porcentagem = int((msg_count / meta) * 100) if meta else 0
        status = "🟢 Ativo" if lock_ativo else "🔴 Inativo"

        await ctx.send(
            f"☕ **Contador Nostalgia**\n"
            f"Status: {status}\n"
            f"Mensagens: {msg_count}/{meta} ({porcentagem}%)\n"
            f"[{barra}]"
        )

async def setup(bot):
    await bot.add_cog(ContadorNostalgia(bot))
