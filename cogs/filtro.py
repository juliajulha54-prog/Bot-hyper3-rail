import discord
from discord.ext import commands
from discord import app_commands
import re
import emoji

# ---------------- REGEX ---------------- #

allowed_links = re.compile(
    r"(https?://)?(www\.)?(streamable\.com|mega\.nz|drive\.google\.com|alightmotion\.com)"
)

emoji_regex = re.compile(r"<a?:\w+:\d+>")

# ---------------- BANCO ---------------- #

async def get_cfg(bot, guild_id):
    return bot.db["filtro"].find_one({"guild_id": str(guild_id)})

async def set_cfg(bot, guild_id, data):
    bot.db["filtro"].update_one(
        {"guild_id": str(guild_id)},
        {"$set": data},
        upsert=True
    )

# ---------------- COG ---------------- #

class Filtro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def status(self, v):
        return "🟢" if v else "🔴"

    # ---------------- EMBED ---------------- #

    async def build_embed(self, guild, cfg, channel_id=None):
        embed = discord.Embed(title="🧹 Filtro Avançado", color=0x2b2d31)

        if not channel_id:
            canais = cfg.get("canais", {})
            txt = []

            for cid in list(canais.keys())[:10]:
                ch = guild.get_channel(int(cid))
                txt.append(ch.mention if ch else f"`{cid}`")

            embed.description = "\n".join(txt) if txt else "❌ Nenhum canal"
            embed.set_footer(text="Selecione um canal")
            return embed

        ch_cfg = cfg["canais"].get(str(channel_id), {})

        embed.description = f"Configuração de <#{channel_id}>"

        embed.add_field(
            name="Permissões",
            value=(
                f"Texto: {self.status(ch_cfg.get('texto', False))}\n"
                f"Emoji: {self.status(ch_cfg.get('emoji', False))}\n"
                f"Links: {self.status(ch_cfg.get('link', True))}\n"
                f"Anexos: {self.status(ch_cfg.get('anexo', True))}\n"
                f"Sticker: {self.status(ch_cfg.get('sticker', False))}"
            ),
            inline=False
        )

        return embed

    # ---------------- VIEW ---------------- #

    class View(discord.ui.View):
        def __init__(self, cog, guild_id, channel_id=None):
            super().__init__(timeout=180)
            self.cog = cog
            self.guild_id = guild_id
            self.channel_id = channel_id

        async def refresh(self, interaction):
            cfg = await get_cfg(self.cog.bot, self.guild_id)

            embed = await self.cog.build_embed(
                interaction.guild,
                cfg,
                self.channel_id
            )

            try:
                await interaction.response.edit_message(embed=embed, view=self)
            except:
                await interaction.message.edit(embed=embed, view=self)

        # -------- SELECIONAR CANAL -------- #

        @discord.ui.button(label="Selecionar Canal")
        async def select_channel(self, i: discord.Interaction, b):
            view = discord.ui.View()
            select = discord.ui.ChannelSelect()

            async def cb(x):
                channel_id = list(x.data["resolved"]["channels"].keys())[0]

                cfg = await get_cfg(self.cog.bot, self.guild_id)
                canais = cfg.setdefault("canais", {})

                if channel_id not in canais:
                    canais[channel_id] = {
                        "texto": False,
                        "emoji": False,
                        "link": True,
                        "anexo": True,
                        "sticker": False
                    }

                await set_cfg(self.cog.bot, self.guild_id, {"canais": canais})

                await x.response.send_message("✅ Canal selecionado", ephemeral=True)

                new_view = Filtro.View(self.cog, self.guild_id, channel_id)
                await i.message.edit(
                    embed=await self.cog.build_embed(i.guild, cfg, channel_id),
                    view=new_view
                )

            select.callback = cb
            view.add_item(select)

            await i.response.send_message("Escolha o canal:", view=view, ephemeral=True)

        # -------- TOGGLES -------- #

        async def toggle(self, key):
            cfg = await get_cfg(self.cog.bot, self.guild_id)
            ch_cfg = cfg["canais"][str(self.channel_id)]

            ch_cfg[key] = not ch_cfg.get(key, False)

            await set_cfg(self.cog.bot, self.guild_id, {"canais": cfg["canais"]})

        @discord.ui.button(label="Texto")
        async def texto(self, i, b):
            await self.toggle("texto")
            await self.refresh(i)

        @discord.ui.button(label="Emoji")
        async def emoji(self, i, b):
            await self.toggle("emoji")
            await self.refresh(i)

        @discord.ui.button(label="Links")
        async def link(self, i, b):
            await self.toggle("link")
            await self.refresh(i)

        @discord.ui.button(label="Anexos")
        async def anexo(self, i, b):
            await self.toggle("anexo")
            await self.refresh(i)

        @discord.ui.button(label="Sticker")
        async def sticker(self, i, b):
            await self.toggle("sticker")
            await self.refresh(i)

    # ---------------- CENTRAL ---------------- #

    async def send_panel(self, target, guild):
        cfg = await get_cfg(self.bot, guild.id)

        if not cfg:
            cfg = {
                "guild_id": str(guild.id),
                "canais": {}
            }
            await set_cfg(self.bot, guild.id, cfg)

        view = self.View(self, guild.id)

        if isinstance(target, discord.Interaction):
            await target.response.send_message(
                embed=await self.build_embed(guild, cfg),
                view=view,
                ephemeral=True
            )
        else:
            await target.send(
                embed=await self.build_embed(guild, cfg),
                view=view
            )

    # ---------------- COMANDOS ---------------- #

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def filtro(self, ctx):
        await self.send_panel(ctx, ctx.guild)

    @app_commands.command(name="filtro", description="Configurar filtro")
    @app_commands.default_permissions(administrator=True)
    async def filtro_slash(self, interaction: discord.Interaction):
        await self.send_panel(interaction, interaction.guild)

    # ---------------- EVENTO ---------------- #

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not m.guild or m.author.bot:
            return

        cfg = await get_cfg(self.bot, m.guild.id)
        if not cfg:
            await self.bot.process_commands(m)
            return

        ch_cfg = cfg.get("canais", {}).get(str(m.channel.id))
        if not ch_cfg:
            await self.bot.process_commands(m)
            return

        # ignora staff
        if m.author.guild_permissions.manage_messages:
            await self.bot.process_commands(m)
            return

        content = m.content.strip()

        has_attachment = len(m.attachments) > 0
        has_link = bool(allowed_links.search(content))
        has_embed = any(e.type in ("video", "image") for e in m.embeds)
        has_custom_emoji = bool(emoji_regex.search(content))
        has_unicode_emoji = emoji.emoji_count(content) > 0
        has_sticker = len(m.stickers) > 0

        is_text = content != ""

        delete = False

        if is_text and not ch_cfg.get("texto"):
            delete = True

        if (has_custom_emoji or has_unicode_emoji) and not ch_cfg.get("emoji"):
            delete = True

        if has_link and not ch_cfg.get("link"):
            delete = True

        if has_attachment and not ch_cfg.get("anexo"):
            delete = True

        if has_sticker and not ch_cfg.get("sticker"):
            delete = True

        if delete:
            try:
                await m.delete()
            except Exception as e:
                print("Erro ao deletar:", e)

        # 🔥 ESSENCIAL
        await self.bot.process_commands(m)

# ---------------- SETUP ---------------- #

async def setup(bot):
    await bot.add_cog(Filtro(bot))
