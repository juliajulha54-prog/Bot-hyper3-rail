import discord
from discord.ext import commands

class LockEveryone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # 🔥 CANAIS IGNORADOS (OS MESMOS DA SUA COG)
        self.canais_ignorados = [
           1468457145182720010,
            1471028250099716127,
            1471585850696405197
        ]

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def lockeveryone(self, ctx):
        msg = await ctx.reply("🔒 | Bloqueando @everyone nos canais...")

        guild = ctx.guild
        everyone = guild.default_role

        canais = [
            c for c in guild.channels
            if isinstance(c, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel))
        ]

        total = len(canais)
        feitos = 0

        for canal in canais:
            try:
                # ❌ IGNORA CANAIS DEFINIDOS
                if canal.id in self.canais_ignorados:
                    continue

                overwrite = canal.overwrites_for(everyone)
                overwrite.view_channel = False
                await canal.set_permissions(everyone, overwrite=overwrite)

                feitos += 1

            except Exception as e:
                print(f"Erro em {canal.name}: {e}")

        await msg.edit(
            content=f"✅ | @everyone bloqueado em {feitos}/{total} canais (ignorados não foram afetados)."
        )

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unlockeveryone(self, ctx):
        msg = await ctx.reply("🔓 | Restaurando @everyone nos canais...")

        guild = ctx.guild
        everyone = guild.default_role

        canais = [
            c for c in guild.channels
            if isinstance(c, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel))
        ]

        feitos = 0

        for canal in canais:
            try:
                overwrite = canal.overwrites_for(everyone)
                overwrite.view_channel = True
                await canal.set_permissions(everyone, overwrite=overwrite)

                feitos += 1

            except Exception as e:
                print(f"Erro em {canal.name}: {e}")

        await msg.edit(
            content=f"✅ | @everyone restaurado em {feitos} canais."
        )

async def setup(bot):
    await bot.add_cog(LockEveryone(bot))
