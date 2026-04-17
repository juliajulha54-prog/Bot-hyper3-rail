import discord
from discord.ext import commands
import time

class Uptime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()  # inicia quando a cog carrega

    def format_time(self, seconds):
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        return f"{days}d {hours}h {minutes}m {secs}s"

    @commands.command(name="uptime")
    async def uptime(self, ctx):
        current_time = time.time()
        uptime_seconds = current_time - self.start_time

        uptime_str = self.format_time(uptime_seconds)

        await ctx.reply(
            f"⏱️ **UPTIME DA AQUA JUBINHA**\n"
            f"<:aquaasleep:1473432813910097922> Online há: `{uptime_str}`\n"
            f"📅 Desde que foi iniciada\n"
            
            
        )

async def setup(bot):
    await bot.add_cog(Uptime(bot))
