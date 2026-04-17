import discord
from discord.ext import commands
from pymongo import MongoClient
import asyncio
import os
import random
from datetime import datetime, timedelta

lock = asyncio.Lock()

# ===============================
# CONFIGURAÇÕES
# ===============================
COOLDOWN_HOURS = 24
MAX_USERS = 1000
MOEDA = "Hyper Golds"

# ===============================
# CONEXÃO MONGO
# ===============================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI não configurado")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client["bot"]
eco_db = db["economia"]

# ===============================
# AUXILIARES
# ===============================

def user_data_default(user_id: int):
    return {
        "_id": str(user_id),
        "saldo": 0,
        "level": 1,
        "exp": 0,
        "last_daily": None
    }

def calc_exp_to_level(level: int):
    return level * 100

def embed_base(title: str, description: str, color=discord.Color.gold()):
    return discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )

# ===============================
# COG
# ===============================

class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ===============================
    # DAILY
    # ===============================
    @commands.command()
    async def daily(self, ctx):
        user_id = str(ctx.author.id)

        async with lock:
            user = eco_db.find_one({"_id": user_id})
            if not user:
                user = user_data_default(user_id)
                eco_db.insert_one(user)

            now = datetime.utcnow()
            last_daily = user.get("last_daily")
            if last_daily:
                last = datetime.strptime(last_daily, "%Y-%m-%d %H:%M:%S")
                if now < last + timedelta(hours=COOLDOWN_HOURS):
                    restante = last + timedelta(hours=COOLDOWN_HOURS) - now
                    h, rem = divmod(int(restante.total_seconds()), 3600)
                    m, s = divmod(rem, 60)
                    return await ctx.reply(
                        f"⏳ Você já coletou seu daily! Tente novamente em `{h}h {m}m {s}s`."
                    )

            ganho = random.randint(50, 200)
            user["saldo"] += ganho
            user["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
            eco_db.update_one({"_id": user_id}, {"$set": user}, upsert=True)

        embed = embed_base(
            "💰 Daily Coletado!",
            f"Você recebeu **{ganho} {MOEDA}**!\nSaldo atual: **{user['saldo']} {MOEDA}**"
        )
        await ctx.send(embed=embed)

    # ===============================
    # SALDO
    # ===============================
    @commands.command()
    async def saldo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user_id = str(member.id)

        user = eco_db.find_one({"_id": user_id})
        if not user:
            user = user_data_default(user_id)
            eco_db.insert_one(user)

        embed = embed_base(
            f"💳 Saldo de {member.display_name}",
            f"Saldo: **{user['saldo']} {MOEDA}**\nLevel: **{user['level']}**\nEXP: **{user['exp']}/{calc_exp_to_level(user['level'])}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # ===============================
    # RANKING (ALTERADO PARA .rank_hg)
    # ===============================
    @commands.command(name="rank_hg")
    async def ranking_hg(self, ctx, top: int = 10):
        top = min(top, 50)
        users = list(eco_db.find())
        if not users:
            return await ctx.reply("Nenhum usuário encontrado.")

        users.sort(key=lambda u: u["saldo"], reverse=True)
        embed = embed_base("🏆 Ranking dos mais ricos", "", color=discord.Color.purple())

        texto = ""
        for i, u in enumerate(users[:top], 1):
            member = ctx.guild.get_member(int(u["_id"]))
            name = member.display_name if member else f"<@{u['_id']}>"
            texto += f"**{i}. {name}** - {u['saldo']} {MOEDA}\n"

        embed.description = texto
        await ctx.send(embed=embed)

    # ===============================
    # LEVEL UP SIMPLES
    # ===============================
    @commands.command()
    async def levelup(self, ctx):
        user_id = str(ctx.author.id)

        async with lock:
            user = eco_db.find_one({"_id": user_id})
            if not user:
                user = user_data_default(user_id)
                eco_db.insert_one(user)

            exp_gain = random.randint(10, 30)
            user["exp"] += exp_gain

            lvl_up = False
            while user["exp"] >= calc_exp_to_level(user["level"]):
                user["exp"] -= calc_exp_to_level(user["level"])
                user["level"] += 1
                lvl_up = True

            eco_db.update_one({"_id": user_id}, {"$set": user}, upsert=True)

        embed = embed_base(
            f"✨ Level Up!",
            f"Você ganhou **{exp_gain} EXP**.\n"
            f"Nível atual: **{user['level']}**\n"
            f"{'🎉 Parabéns! Você subiu de nível!' if lvl_up else ''}",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

# ===============================
# SETUP
# ===============================
async def setup(bot):
    await bot.add_cog(Economia(bot))
