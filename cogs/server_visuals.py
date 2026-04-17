import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import aiohttp
import random

SERVER_ID = 1486183507519865024  # <--- servidor específico

class Banner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db["banners"]
        self.cache = {}
        self.loop_banner.start()

    def cog_unload(self):
        self.loop_banner.cancel()

    # ===============================
    # LOOP AUTOMÁTICO (30 MIN)
    # ===============================
    @tasks.loop(minutes=30)
    async def loop_banner(self):
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(SERVER_ID)
        if not guild:
            return
        try:
            data = self.db.find_one({"_id": guild.id})
            if not data or not data.get("banners"):
                return

            banner_url = random.choice(data["banners"])
            if banner_url in self.cache:
                img = self.cache[banner_url]
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(banner_url) as resp:
                        if resp.status != 200:
                            return
                        img = await resp.read()
                        self.cache[banner_url] = img

            await guild.edit(banner=img)
            print(f"✅ Banner trocado em {guild.name}")
        except Exception as e:
            print(f"❌ Erro no banner ({guild.name}): {e}")

    @loop_banner.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        print("🔄 Sistema de banner iniciado (30min)")

    # ===============================
    # ADICIONAR BANNER (preview)
    # ===============================
    @commands.command()
    async def addbanner(self, ctx, link: str):
        if ctx.guild.id != SERVER_ID:
            return await ctx.reply("❌ Comando disponível apenas neste servidor.", ephemeral=True)
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.reply("**❌ | Você precisa da permissão `Gerenciar Servidor` para adicionar banners.**", ephemeral=True)

        embed = discord.Embed(
            title="🖼️ Preview do banner",
            description=f"Link: {link}\nClique ✅ para confirmar ou ❌ para cancelar.",
            color=discord.Color.from_str("#ff0000")
        )
        embed.set_image(url=link)

        class ConfirmView(View):
            def __init__(self, ctx, link):
                super().__init__(timeout=60)
                self.ctx = ctx
                self.link = link

            @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.secondary, emoji="✅")
            async def confirm(self, interaction: discord.Interaction, button: Button):
                if interaction.user != self.ctx.author:
                    return await interaction.response.send_message("**❌ | Apenas quem iniciou pode confirmar.**", ephemeral=True)

                self.ctx.bot.db["banners"].update_one(
                    {"_id": self.ctx.guild.id},
                    {"$push": {"banners": self.link}},
                    upsert=True
                )
                await interaction.response.edit_message(embed=discord.Embed(
                    title="✅ | Banner adicionado!",
                    color=discord.Color.from_str("#ff0000")
                ), view=None)

            @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
            async def cancel(self, interaction: discord.Interaction, button: Button):
                if interaction.user != self.ctx.author:
                    return await interaction.response.send_message("**❌ | Apenas quem iniciou pode cancelar.**", ephemeral=True)

                await interaction.response.edit_message(embed=discord.Embed(
                    title="**❌ | Adição cancelada**",
                    color=discord.Color.from_str("#ff0000")
                ), view=None)

        await ctx.reply(embed=embed, view=ConfirmView(ctx, link))

    # ===============================
    # TROCAR MANUAL
    # ===============================
    @commands.command()
    async def trocarbanner(self, ctx):
        if ctx.guild.id != SERVER_ID:
            return await ctx.reply("❌ Comando disponível apenas neste servidor.", ephemeral=True)

        data = self.db.find_one({"_id": ctx.guild.id})
        if not data or not data.get("banners"):
            return await ctx.reply("❌ Nenhum banner cadastrado.", ephemeral=True)

        banner_url = random.choice(data["banners"])
        try:
            if banner_url in self.cache:
                img = self.cache[banner_url]
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(banner_url) as resp:
                        if resp.status != 200:
                            return await ctx.reply("❌ | Erro ao baixar banner.", ephemeral=True)
                        img = await resp.read()
                        self.cache[banner_url] = img

            await ctx.guild.edit(banner=img)
            embed = discord.Embed(
                title="✅ | Banner trocado manualmente",
                description=f"Banner alterado com sucesso!",
                color=discord.Color.from_str("#ff0000")
            )
            embed.set_image(url=banner_url)
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(embed=discord.Embed(
                title="❌ Erro ao trocar banner.",
                color=discord.Color.from_str("#ff0000")
            ))
            print(e)

    # ===============================
    # LISTAR BANNERS (navegação + remoção)
    # ===============================
    @commands.command()
    async def banners(self, ctx):
        if ctx.guild.id != SERVER_ID:
            return await ctx.reply("❌ Comando disponível apenas neste servidor.", ephemeral=True)

        data = self.db.find_one({"_id": ctx.guild.id})
        if not data or not data.get("banners"):
            return await ctx.reply("❌ Nenhum banner salvo.", ephemeral=True)

        banners_list = data["banners"]

        class BannerView(View):
            def __init__(self, ctx, banners_list):
                super().__init__(timeout=None)
                self.ctx = ctx
                self.banners_list = banners_list
                self.current = 0
                self.removed = False  # <-- marca se o banner foi removido

            def get_embed(self):
                if self.removed:
                    return discord.Embed(
                        description="```Imagem removida```",
                        color=discord.Color.from_str("#ff0000")
                    )
                embed = discord.Embed(
                    title="🖼️ Banners cadastrados",
                    description=f"Banner {self.current + 1}/{len(self.banners_list)}",
                    color=discord.Color.from_str("#ff0000")
                )
                embed.set_image(url=self.banners_list[self.current])
                return embed

            # Seta custom
            @discord.ui.button(label="", style=discord.ButtonStyle.secondary, emoji="<a:seta_red:1469720979201851414>")
            async def next_banner(self, interaction: discord.Interaction, button: Button):
                if not self.banners_list:  # se não houver banners
                    return
                self.removed = False
                self.current = (self.current + 1) % len(self.banners_list)
                await interaction.response.edit_message(embed=self.get_embed(), view=self)

            # Lixeira custom
            @discord.ui.button(label="", style=discord.ButtonStyle.secondary, emoji="<:c_1Lixeira1:1483989732508696629>")
            async def remove_banner(self, interaction: discord.Interaction, button: Button):
                if not interaction.user.guild_permissions.manage_guild:
                    return await interaction.response.send_message(
                        "**❌ | Você precisa da permissão `Gerenciar Servidor`.**", ephemeral=True
                    )
                self.banners_list.pop(self.current)
                self.ctx.bot.db["banners"].update_one(
                    {"_id": self.ctx.guild.id}, {"$set": {"banners": self.banners_list}}
                )
                self.removed = True
                await interaction.response.edit_message(embed=self.get_embed(), view=self)

        await ctx.reply(embed=BannerView(ctx, banners_list).get_embed(), view=BannerView(ctx, banners_list))

# ===============================
# SETUP
# ===============================
async def setup(bot):
    await bot.add_cog(Banner(bot))
