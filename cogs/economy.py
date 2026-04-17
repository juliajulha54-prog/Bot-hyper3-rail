import discord
from discord.ext import commands
import random
import time

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db["users"]

    # ===============================
    # GET USER
    # ===============================
    def get_user(self, user_id):
        user = self.db.find_one({"_id": user_id})
        if not user:
            user = {
                "_id": user_id,
                "coins": 0,
                "level": 1,
                "xp": 0,
                "last_work": 0,
                "transactions": []
            }
            self.db.insert_one(user)
        return user

    # ===============================
    # WORK
    # ===============================
    @commands.command()
    async def work(self, ctx):
        user = self.get_user(ctx.author.id)

        now = time.time()
        if now - user["last_work"] < 1800:
            restante = int(1800 - (now - user["last_work"])) // 60
            return await ctx.reply(f"❌ | Você já trabalhou recentemente. Volte em: **{restante} minutos**.")

        ganho = random.randint(1500, 3000)

        self.db.update_one(
            {"_id": ctx.author.id},
            {
                "$inc": {"coins": ganho, "xp": 20},
                "$set": {"last_work": now},
                "$push": {
                    "transactions": {
                        "type": "work",
                        "amount": ganho,
                        "time": int(now)
                    }
                }
            }
        )

        await ctx.reply(f"💼 | Você trabalhou e recebeu **{ganho} Hyper Golds**!")

    # ===============================
    # COINS / BAL
    # ===============================
    @commands.command(aliases=["bal"])
    async def coins(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        data = self.get_user(user.id)

        await ctx.reply(
            f"💰 **| {user.mention} possui {data['coins']:,} Hyper Golds!**"
        )

    # ===============================
    # LEVEL
    # ===============================
    @commands.command()
    async def level(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        data = self.get_user(user.id)

        await ctx.reply(
            f"🚀 **| {user.mention} está no nível {data['level']}**"
        )

    # ===============================
    # UP
    # ===============================
    @commands.command()
    async def up(self, ctx):
        user = self.get_user(ctx.author.id)

        custo = user["level"] * 5000

        if user["coins"] < custo:
            return await ctx.reply("❌ | Você não tem coins suficientes.")

        self.db.update_one(
            {"_id": ctx.author.id},
            {
                "$inc": {"coins": -custo, "level": 1}
            }
        )

        await ctx.reply(f"⬆️ | Você upou! Novo nível: **{user['level'] + 1}**")

    # ===============================
    # PIX
    # ===============================
    @commands.command()
    async def pix(self, ctx, user: discord.Member, valor: int):
        if valor <= 0:
            return await ctx.reply("❌ | Valor inválido.")

        author = self.get_user(ctx.author.id)
        target = self.get_user(user.id)

        if author["coins"] < valor:
            return await ctx.reply("❌ | Você não tem saldo suficiente.")

        self.db.update_one({"_id": ctx.author.id}, {"$inc": {"coins": -valor}})
        self.db.update_one({"_id": user.id}, {"$inc": {"coins": valor}})

        await ctx.reply(f"💸 | Você enviou **{valor} Hyper Golds** para {user.mention}.")

    # ===============================
    # RANK
    # ===============================
    @commands.command()
    async def rank(self, ctx):
        top = self.db.find().sort("coins", -1).limit(10)

        msg = ""
        for i, user in enumerate(top, 1):
            member = ctx.guild.get_member(user["_id"])
            nome = member.name if member else "Usuário"
            msg += f"**{i}. {nome}** - {user['coins']:,}\n"

        embed = discord.Embed(
            title="🏆 Ranking de Hyper Golds",
            description=msg,
            color=discord.Color.from_str("#ff0000")
        )

        await ctx.reply(embed=embed)

    # ===============================
    # RANKUP
    # ===============================
    @commands.command()
    async def rankup(self, ctx):
        top = self.db.find().sort("level", -1).limit(10)

        msg = ""
        for i, user in enumerate(top, 1):
            member = ctx.guild.get_member(user["_id"])
            nome = member.name if member else "Usuário"
            msg += f"**{i}. {nome}** - Nível {user['level']}\n"

        embed = discord.Embed(
            title="🏆 Ranking de Levels",
            description=msg,
            color=discord.Color.from_str("#ff0000")
        )

        await ctx.reply(embed=embed)

    # ===============================
    # TRANSAÇÕES
    # ===============================
    @commands.command()
    async def transações(self, ctx):
        user = self.get_user(ctx.author.id)
        trans = user["transactions"][-25:]

        if not trans:
            return await ctx.reply("❌ | Nenhuma transação encontrada.")

        msg = ""
        for t in trans[::-1]:
            msg += f"💰 {t['type']} +{t['amount']}\n"

        embed = discord.Embed(
            title="📄 Últimas transações",
            description=msg,
            color=discord.Color.from_str("#ff0000")
        )

        await ctx.reply(embed=embed)

    # ===============================
    # PERFIL (IGUAL PRINT)
    # ===============================
    @commands.command()
    async def perfil(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        data = self.get_user(user.id)

        embed = discord.Embed(
            description=(
                f"👤 | Perfil de {user.name}\n\n"
                f"💰 | Hyper Golds: {data['coins']:,}\n"
                f"🚀 | Level: {data['level']}\n"
                f"🏆 | Rank: calculando...\n"
            ),
            color=discord.Color.from_str("#ff0000")
        )

        await ctx.reply(embed=embed)

# ===============================
# SETUP
# ===============================
async def setup(bot):
    await bot.add_cog(Economy(bot))
