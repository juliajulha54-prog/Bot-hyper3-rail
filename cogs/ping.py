import discord
from discord.ext import commands
import time

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx):
        # Gateway ping
        gateway_ping = round(self.bot.latency * 1000)

        # API ping
        start = time.perf_counter()
        msg = await ctx.reply("🏓 Calculando ping...")
        end = time.perf_counter()

        api_ping = round((end - start) * 1000)

        # Shard info
        shard_id = getattr(ctx.guild, "shard_id", 0) if ctx.guild else 0
        shard_count = self.bot.shard_count or 1

        # Cluster fake (customizável)
        cluster_name = "Aqua"
        cluster_id = 6

        await msg.edit(content=
            f":ping_pong: **|** **Pong!** "
            f"(📡 Shard {shard_id}/{shard_count}) "
            f"(<:h_aquathinker:1470083923710316597> Aqua Cluster {cluster_id} (`{cluster_name}`))\n"
            f":stopwatch: **|** **Gateway Ping:** `{gateway_ping}ms`\n"
            f":zap: **|** **API Ping:** `{api_ping}ms`"
        )

async def setup(bot):
    await bot.add_cog(Ping(bot))
