import discord
from discord.ext import commands
from discord import app_commands
import re

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
        return "🟢 Ativado" if v else "🔴 Desativado"

    async def build_embed(self, guild, cfg):
        canais = cfg.get("canais", [])
        canais_fmt = []

        for c in canais[:10]:
            ch = guild.get_channel(int(c))
            canais_fmt.append(ch.mention if ch else f"`{c}`")

        if not canais_fmt:
            canais_fmt = ["❌ Nenhum canal"]

        embed = discord.Embed(
            title="🧹 Filtro de Conteúdo",
            color=0x2b2d31
        )

        embed.add_field(name="Status", value=self.status(cfg.get("ativo")), inline=True)
        embed.add_field(name="Canais", value="\n".join(canais_fmt), inline=False)

        return embed

    # ---------------- VIEW ---------------- #

    class View(discord.ui.View):
        def __init__(self, cog, guild_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.guild_id = guild_id

        async def update(self, interaction):
            cfg = await get_cfg(self.cog.bot, self.guild_id)

            await interaction.response.edit_message(
                embed=await self.cog.build_embed(interaction.guild, cfg),
                view=self
            )

        @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.blurple)
        async def toggle(self, i: discord.Interaction, b):
            cfg = await get_cfg(self.cog.bot, self.guild_id)

            await set_cfg(self.cog.bot, self.guild_id, {
                "ativo": not cfg.get("ativo", False)
            })

            await self.update(i)

        @discord.ui.button(label="Canais")
        async def canais(self, i: discord.Interaction, b):
            view = discord.ui.View()
            select = discord.ui.ChannelSelect()

            async def cb(x):
                cfg = await get_cfg(self.cog.bot, self.guild_id)
                canais = cfg.get("canais", [])

                channel_id = list(x.data["resolved"]["channels"].keys())[0]

                if channel_id in canais:
                    canais.remove(channel_id)
                    msg = "❌ Canal removido."
                else:
                    canais.append(channel_id)
                    msg = "✅ Canal adicionado."

                await set_cfg(self.cog.bot, self.guild_id, {
                    "canais": canais
                })

                await x.response.send_message(msg, ephemeral=True)

            select.callback = cb
            view.add_item(select)

            await i.response.send_message(
                "Selecione um canal:",
                view=view,
                ephemeral=True
            )

    # ---------------- SLASH ---------------- #

    @app_commands.command(name="filtro", description="Configurar filtro de conteúdo")
    @app_commands.check(lambda i: i.user.guild_permissions.administrator)
    async def filtro(self, interaction: discord.Interaction):

        cfg = await get_cfg(self.bot, interaction.guild.id)

        if not cfg:
            cfg = {
                "guild_id": str(interaction.guild.id),
                "ativo": False,
                "canais": []
            }
            await set_cfg(self.bot, interaction.guild.id, cfg)

        await interaction.response.send_message(
            embed=await self.build_embed(interaction.guild, cfg),
            view=self.View(self, interaction.guild.id),
            ephemeral=True
        )

    # ---------------- EVENTO ---------------- #

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not m.guild or m.author.bot:
            return

        if m.author.guild_permissions.manage_messages:
            return

        cfg = await get_cfg(self.bot, m.guild.id)

        if not cfg or not cfg.get("ativo"):
            return

        if str(m.channel.id) not in cfg.get("canais", []):
            return

        content = m.content.strip()

        has_attachment = len(m.attachments) > 0
        has_allowed_link = bool(allowed_links.search(content))
        has_embed = any(e.type in ("video", "image") for e in m.embeds)
        has_emoji = bool(emoji_regex.search(content))
        has_sticker = len(m.stickers) > 0

        is_plain_text = (
            content != "" and
            not has_attachment and
            not has_allowed_link and
            not has_embed
        )

        if is_plain_text or has_emoji or has_sticker:
            try:
                await m.delete()
            except:
                pass

# ---------------- SETUP ---------------- #

async def setup(bot):
    await bot.add_cog(Filtro(bot))
