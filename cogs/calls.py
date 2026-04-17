import discord
from discord.ext import commands

class Calls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="criarcalls")
    @commands.has_permissions(manage_channels=True)
    async def criarcalls(self, ctx):
        guild = ctx.guild

        # Categoria
        categoria_nome = "CANAIS DE VOZ"
        categoria = discord.utils.get(guild.categories, name=categoria_nome)

        if categoria is None:
            categoria = await guild.create_category(categoria_nome)

        # Nomes das calls
        calls_nomes = [
            "🔊 | bate-papo",
            "🎮 | jogando",
            "⚡ | editando",
            "💤 | afk"
        ]

        criadas = []

        for nome in calls_nomes:
            canal = discord.utils.get(guild.voice_channels, name=nome)

            if canal is None:
                canal = await guild.create_voice_channel(
                    name=nome,
                    category=categoria
                )

            criadas.append(canal)

        mensagem = "✅ **Calls criadas:**\n\n"
        for canal in criadas:
            mensagem += f"{canal.mention}\n"

        await ctx.send(mensagem)


async def setup(bot):
    await bot.add_cog(Calls(bot))
