import discord
from discord.ext import commands
import io
import contextlib
import traceback

DONOS = [
    1213289963878228068,
    932012274569338981,
    569633804537430036, 1470435872066502833, 1470445922549895179, 932011766651703358
]

class Eval(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="eval")
    async def eval_cmd(self, ctx, *, codigo: str):

        if ctx.author.id not in DONOS:
            return await ctx.reply("**🚫 | Somente os donos do bot podem usar este comando.**")

        await ctx.reply("⚙️ Executando código...")

        if codigo.startswith("```"):
            codigo = "\n".join(codigo.split("\n")[1:-1])

        stdout = io.StringIO()

        try:
            exec_code = "async def _exec(ctx, bot, db, votacoes_db, economia_db):\n"
            for linha in codigo.split("\n"):
                exec_code += f"    {linha}\n"

            local_vars = {}
            exec(exec_code, globals(), local_vars)

            with contextlib.redirect_stdout(stdout):
                resultado = await local_vars["_exec"](
                    ctx,
                    self.bot,
                    getattr(self.bot, "db", None),
                    getattr(self.bot, "votacoes_db", None),
                    getattr(self.bot, "economia_db", None)
                )

            saida = stdout.getvalue()

            resposta = "✅ **Código executado com sucesso!**\n"

            if saida:
                if len(saida) > 1900:
                    saida = saida[:1900] + "\n... (cortado)"
                resposta += f"📤 Saída:\n```py\n{saida}\n```"

            if resultado is not None:
                resultado_str = str(resultado)
                if len(resultado_str) > 1900:
                    resultado_str = resultado_str[:1900] + "\n... (cortado)"
                resposta += f"\n📥 Retorno:\n```py\n{resultado_str}\n```"

            if not saida and resultado is None:
                resposta += "ℹ️ Nenhuma saída foi produzida."

            await ctx.send(resposta)

        except Exception:
            erro = traceback.format_exc()
            if len(erro) > 1900:
                erro = erro[:1900] + "\n... (cortado)"
            await ctx.send(
                f"❌ **Erro ao executar o código:**\n```py\n{erro}\n```"
            )

async def setup(bot):
    await bot.add_cog(Eval(bot))
