import discord
from discord.ext import commands
import re

class Categorias(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ===============================
    # 🔧 FORMATADOR DE NOME
    # ===============================
    def formatar_nome(self, nome):
        # remove padrões antigos tipo ╭─ ✧ etc
        nome_limpo = re.sub(r"^[^\w\d]+", "", nome).strip()

        # tenta separar emoji do resto
        partes = nome_limpo.split(" ", 1)

        if len(partes) > 1 and len(partes[0]) <= 3:
            emoji = partes[0]
            texto = partes[1]
            return f"╭─{emoji} ✧ {texto}"
        else:
            return f"╭─☕ ✧ {nome_limpo}"

    # ===============================
    # 📂 COMANDO PRINCIPAL
    # ===============================
    @commands.command(name="arrumarcategorias")
    @commands.has_permissions(administrator=True)
    async def arrumar_categorias(self, ctx):
        await ctx.send("🔧 Arrumando categorias...")

        alteradas = 0

        for categoria in ctx.guild.categories:
            novo_nome = self.formatar_nome(categoria.name)

            if categoria.name != novo_nome:
                try:
                    await categoria.edit(name=novo_nome)
                    alteradas += 1
                except Exception as e:
                    print(f"Erro ao editar {categoria.name}: {e}")

        await ctx.send(f"✅ Categorias atualizadas: {alteradas}")

    # ===============================
    # ⚡ AUTO AO INICIAR (OPCIONAL)
    # ===============================
    @commands.Cog.listener()
    async def on_ready(self):
        print("📂 Cog de categorias carregada!")

async def setup(bot):
    await bot.add_cog(Categorias(bot))
