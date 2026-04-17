import discord
from discord.ext import commands
import json
import os

VS = "<:z_vs:1475544356479041546>"
ARQUIVO = "torneio_dados.json"
VOTOS_ARQ = "votos.json"


class Torneio(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.carregar_dados()

    # ---------------- SALVAR ----------------

    def salvar(self):
        dados = {
            "quartas": self.quartas,
            "semi": self.semi,
            "final": self.final,
            "especial": self.especial,
            "grande_final": self.grande_final
        }

        with open(ARQUIVO, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4)

    # ---------------- CARREGAR ----------------

    def carregar_dados(self):

        if os.path.exists(ARQUIVO):
            with open(ARQUIVO, "r", encoding="utf-8") as f:
                dados = json.load(f)

            self.quartas = dados.get("quartas", [])
            self.semi = dados.get("semi", [])
            self.final = dados.get("final", [None, None, None])
            self.especial = dados.get("especial", [None, None, None])
            self.grande_final = dados.get("grande_final", [None, None, None])
        else:
            self.resetar_dados()

    # ---------------- RESET ----------------

    def resetar_dados(self):

        self.quartas = [
            ["kerbvfx","mui",None],
            ["mendes","duardo",None],
            ["RTZ","Lima",None],
            ["Shino","Dan",None],
            ["Arthur","fis",None]
        ]

        self.semi = [
            [None,None,None],
            [None,None,None],
            [None,None,None]
        ]

        self.final = [None,None,None]
        self.especial = ["Retuurn","Geraldão",None]
        self.grande_final = [None,None,None]

        self.salvar()

    # ---------------- EMBED ----------------

    def embed_tabela(self):

        desc = "🔥 **Quartas**\n\n"

        for a,b,v in self.quartas:

            if v is None:
                desc += f"{a} {VS} {b} → ⌛\n"
            else:
                perdedor = b if v == a else a
                desc += f"{a} {VS} {b} → 👑 {v}\n"
                desc += f"❌ {perdedor} eliminado\n"

        desc += "\n⚔ **Semifinal**\n\n"

        for a,b,v in self.semi:

            if a is None:
                continue

            elif v is None:
                desc += f"{a} {VS} {b} → ⌛\n"

            elif v == "EMPATE":
                desc += f"{a} {VS} {b} → 👑 EMPATE: kerb passou para a GRANDE FINAL e fis irá contra o mendes.\n"

            else:
                perdedor = b if v == a else a
                desc += f"{a} {VS} {b} → 👑 {v}\n"
                desc += f"❌ {perdedor} eliminado\n"

        desc += "\n🏆 **Final**\n\n"

        a,b,v = self.final

        if a:
            if b is None:
                desc += f"{a} {VS} ? → ⌛\n"
            elif v is None:
                desc += f"{a} {VS} {b} → ⌛\n"
            else:
                perdedor = b if v == a else a
                desc += f"{a} {VS} {b} → 👑 {v}\n"
                desc += f"❌ {perdedor} eliminado\n"

        desc += "\n💀 **Confronto Especial**\n\n"

        a,b,v = self.especial

        if v is None:
            desc += f"{a} {VS} {b} → ⌛\n"
        else:
            desc += f"{a} {VS} {b} → 👑 {v}\n"

        desc += "\n**## Grande Final**\n\n"

        a,b,v = self.grande_final

        if a:
            desc += f"{a} {VS} ? → ⌛\n"
        else:
            desc += f"? {VS} ? → ⌛\n"

        return discord.Embed(
            title="🏆 Torneio de Edição",
            description=desc,
            color=discord.Color.gold()
        )

    # ---------------- COMANDOS ----------------

    @commands.command()
    async def tabela(self, ctx):
        await ctx.reply(embed=self.embed_tabela())

    # ⭐ AJUSTE DA TABELA (igual você já tinha)

    @commands.command()
    async def ajustar_tabela(self, ctx):

        if not ctx.author.guild_permissions.manage_guild:
            await ctx.reply("❌ Sem permissão.")
            return

        self.grande_final[0] = "kerbvfx"

        self.semi = [
            ["fis", "kerbvfx", "EMPATE"],
            ["Lima", "Dan", "Dan"],
            ["mendes", "fis", None]
        ]

        self.final = ["Dan", None, None]

        self.salvar()

        await ctx.reply("✅ Tabela ajustada.")

    # 🏆 VENCEDOR DA FINAL

    @commands.command()
    async def vencedor(self, ctx):

        if not os.path.exists(VOTOS_ARQ):
            await ctx.reply("❌ votos.json não encontrado.")
            return

        with open(VOTOS_ARQ, "r", encoding="utf-8") as f:
            dados = json.load(f)

        votacao = dados["votacoes"].get("Dan_vs_fis")

        if not votacao:
            await ctx.reply("❌ Votação não encontrada.")
            return

        contagem = votacao["contagem"]

        dan = contagem.get("Dan", 0)
        fis = contagem.get("fis", 0)

        if dan > fis:
            vencedor = "Dan"
            vice = "fis"
        else:
            vencedor = "fis"
            vice = "Dan"

        # Atualiza FINAL sem mexer na estrutura
        self.final = ["Dan", "fis", vencedor]
        self.salvar()

        embed = discord.Embed(
            title="<:c321df5a4dfbe97b95157720f9a7f2a5:1479267367375863960> CAMPEÃO DA CATEGORIA AFTER MOTION",
            description=(
                f"🔥 O participante **{vencedor}** GANHOU A FINAL!!!\n\n"
                f"👑 Agora ele se tornou o <@&1478835955514343444> na categoria <@&1468659338661986470> PARABÉNS!!!.\n\n"
                f"🥈 Vice-campeã 2° lugar\ntambém na categoria <@&1468659338661986470>: **{vice}**\n"
                f"Parabéns fis!!! \n\n"
                f"💛 Obrigado a todos que participaram e votaram! mesmo com alguns bugs no bot, mas os votos foram computados corretamente rsrs"
            ),
            color=discord.Color.gold()
        )

        await ctx.reply(embed=embed)

    # 🥇 RANKING FINAL

    @commands.command()
    async def ranke(self, ctx):

        if not os.path.exists(VOTOS_ARQ):
            await ctx.reply("❌ votos.json não encontrado.")
            return

        with open(VOTOS_ARQ, "r", encoding="utf-8") as f:
            dados = json.load(f)

        votacao = dados["votacoes"].get("Dan_vs_fis")

        if not votacao:
            await ctx.reply("❌ Dados não encontrados.")
            return

        contagem = votacao["contagem"]

        dan = contagem.get("Dan", 0)
        fis = contagem.get("fis", 0)

        if dan > fis:
            primeiro = ("Dan", dan)
            segundo = ("fis", fis)
        else:
            primeiro = ("fis", fis)
            segundo = ("Dan", dan)

        terceiro = "Lima"

        embed = discord.Embed(
            title="🏆 Ranking Final",
            description=(
                f"## Categoria: <@&1468659338661986470>\n🥇 **1º Lugar:** {primeiro[0]} — {primeiro[1]} votos\n"
                f"🥈 **2º Lugar:** {segundo[0]} — {segundo[1]} votos\n"
                f"🥉 **3º Lugar: {terceiro} entregou a vitória com 15 votos.\n🔥 Parabéns a todos os competidores!**"
            ),
            color=discord.Color.orange()
        )

        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(Torneio(bot))
