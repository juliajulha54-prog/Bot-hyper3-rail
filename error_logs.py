import traceback
from discord.ext import commands

class ErrorLogs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        with open("erros.txt", "a", encoding="utf-8") as f:
            f.write(f"\nERRO NO COMANDO: {ctx.command}\n")
            f.write(f"USUARIO: {ctx.author}\n")
            f.write(traceback.format_exc())
            f.write("\n------------------------\n")

async def setup(bot):
    await bot.add_cog(ErrorLogs(bot))