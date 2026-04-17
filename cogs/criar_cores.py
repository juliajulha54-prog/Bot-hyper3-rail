import discord
from discord.ext import commands

SERVIDOR_ORIGEM_ID = 1484060471555264633
SERVIDOR_DESTINO_ID = 1486183507519865024

class CriarCores(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def debug_core(self, ctx):
        origem = self.bot.get_guild(SERVIDOR_ORIGEM_ID)
        destino = self.bot.get_guild(SERVIDOR_DESTINO_ID)

        msg = "📊 DEBUG\n\n"
        msg += f"Origem encontrada: {origem is not None}\n"
        msg += f"Destino encontrado: {destino is not None}\n"

        if destino:
            cargo = discord.utils.get(destino.roles, name="carl-bot")
            msg += f"Cargo 'carl-bot' existe: {cargo is not None}\n"

            bot_member = destino.get_member(self.bot.user.id)
            if bot_member:
                msg += f"Permissão gerenciar cargos: {bot_member.guild_permissions.manage_roles}\n"
                msg += f"Cargo mais alto do bot: {bot_member.top_role.position}\n"

        await ctx.send(msg)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def copiarcores(self, ctx):
        origem = self.bot.get_guild(SERVIDOR_ORIGEM_ID)
        destino = self.bot.get_guild(SERVIDOR_DESTINO_ID)

        if not origem:
            return await ctx.send("❌ Bot não está no servidor de origem")

        if not destino:
            return await ctx.send("❌ ID do servidor destino está errado")

        cargo_base = discord.utils.get(destino.roles, name="carl-bot")
        if not cargo_base:
            return await ctx.send("❌ Cargo 'carl-bot' não encontrado")

        bot_member = destino.get_member(self.bot.user.id)

        if not bot_member.guild_permissions.manage_roles:
            return await ctx.send("❌ Sem permissão de gerenciar cargos")

        if bot_member.top_role.position <= cargo_base.position:
            return await ctx.send("❌ Cargo do bot está abaixo do 'carl-bot'")

        await ctx.send("⏳ Copiando cargos...")

        cargos_criados = []

        for role in origem.roles:
            if role.is_default() or role.color.value == 0:
                continue

            try:
                novo = await destino.create_role(
                    name=f"✦ {role.name}",
                    color=role.color,
                    mentionable=True
                )
                cargos_criados.append(novo)

            except Exception as e:
                print(e)

        try:
            base = cargo_base.position
            cargos_criados.reverse()

            for i, r in enumerate(cargos_criados):
                await r.edit(position=base - i - 1)

        except Exception as e:
            print(e)

        if cargos_criados:
            texto = "🎨 Cargos criados:\n"
            for r in cargos_criados:
                if len(texto) > 1800:
                    await ctx.send(texto)
                    texto = ""
                texto += f"{r.mention} "

            if texto:
                await ctx.send(texto)

        await ctx.send(f"✅ {len(cargos_criados)} cargos criados!")

async def setup(bot):
    await bot.add_cog(CriarCores(bot))
