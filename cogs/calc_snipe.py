import discord
from discord.ext import commands
import datetime
import ast
import operator

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.snipes = {}  # channel_id: {content, author, time}

    # =========================
    # 📌 SNIPE
    # =========================
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        self.snipes[message.channel.id] = {
            "content": message.content,
            "author": message.author,
            "time": datetime.datetime.now()
        }

    @commands.command()
    async def snipe(self, ctx):
        data = self.snipes.get(ctx.channel.id)

        if not data:
            return await ctx.reply(
                "**<:dh_fkAquaCry:1473431628880548032> | Nada para snipar aqui... ninguém fez bagunça ainda!**"
            )

        embed = discord.Embed(
            description=f"**{data['content'] or '*mensagem vazia*'}**",
            color=0x00bfff,
            timestamp=data["time"]
        )

        embed.set_author(
            name=f"{data['author']}",
            icon_url=data['author'].display_avatar.url
        )

        embed.set_footer(text=" <:h_aquathinker:1470083923710316597> Eu vejo tudo...")

        await ctx.reply(embed=embed)

    # =========================
    # 🧮 CALCULADORA SEGURA
    # =========================
    def safe_eval(self, expr):
        allowed_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod
        }

        def eval_node(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                if type(node.op) not in allowed_operators:
                    raise ValueError("Operador inválido")
                return allowed_operators[type(node.op)](
                    eval_node(node.left),
                    eval_node(node.right)
                )
            else:
                raise ValueError("Expressão inválida")

        tree = ast.parse(expr, mode='eval')
        return eval_node(tree.body)

    @commands.command()
    async def calc(self, ctx, *, conta: str):
        try:
            resultado = self.safe_eval(conta)

            await ctx.reply(
                f"** <:h_aquathinker:1470083923710316597> | Resultado:** `{resultado}`\n"
                f" ✨ | Conta: `{conta}`"
            )

        except Exception:
            await ctx.reply(
                "**<:dh_fkAquaCry:1473431628880548032> | E-eh?! Essa conta parece estranha... tenta de novo por favor!**"
            )


async def setup(bot):
    await bot.add_cog(Utility(bot))
