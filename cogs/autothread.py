import discord
from discord.ext import commands
from discord import app_commands

# ---------------- BANCO ----------------

async def get_cfg(bot, guild_id):
    if not hasattr(bot, "db") or bot.db is None:
        return {}

    try:
        col = bot.db["autothreads"]
        data = await col.find_one({"guild_id": str(guild_id)})
        return data if data else {}
    except Exception as e:
        print(f"Erro DB GET: {e}")
        return {}


async def set_cfg(bot, guild_id, update_dict):
    if not hasattr(bot, "db") or bot.db is None:
        return

    try:
        col = bot.db["autothreads"]
        await col.update_one(
            {"guild_id": str(guild_id)},
            {"$set": update_dict},
            upsert=True
        )
    except Exception as e:
        print(f"Erro DB SET: {e}")


# ---------------- UTIL ----------------

async def get_panel_message(bot, guild):
    cfg = await get_cfg(bot, guild.id)
    msg_id = cfg.get("panel_message_id")

    if not msg_id:
        return None

    for channel in guild.text_channels:
        try:
            msg = await channel.fetch_message(int(msg_id))
            return msg
        except:
            continue

    return None


# ---------------- COG ----------------

class EasyThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_status(self, value):
        return "🟢 `Ativado`" if value else "🔴 `Desativado`"

    async def build_embed(self, guild):
        cfg = await get_cfg(self.bot, guild.id)

        channel_id = cfg.get("channel_id")
        canal = guild.get_channel(int(channel_id)) if channel_id else None

        embed = discord.Embed(title="🧵 Painel Easy Threads", color=0x2b2d31)

        embed.add_field(
            name="📍 Canal Alvo",
            value=canal.mention if canal else "❌ `Não definido`",
            inline=True
        )

        embed.add_field(
            name="Status Geral",
            value=self.get_status(cfg.get("ativo")),
            inline=True
        )

        embed.add_field(
            name="📝 Definições",
            value=(
                f"Nome: `{cfg.get('nome', 'Thread de {{user}}')}`\n"
                f"Mensagem: `{cfg.get('mensagem', 'Sua thread foi criada.')[:50]}`"
            ),
            inline=False
        )

        embed.add_field(
            name="⚙️ Opções",
            value=(
                f"Ignorar Bots: {self.get_status(cfg.get('ignorebots'))}\n"
                f"Fixar Mensagem: {self.get_status(cfg.get('pin'))}\n"
                f"Thread Privada: {self.get_status(cfg.get('private'))}"
            ),
            inline=False
        )

        return embed

    # ---------------- VIEW ----------------

    class MainView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        async def update_panel(self, guild):
            panel = await get_panel_message(self.cog.bot, guild)
            if panel:
                await panel.edit(
                    embed=await self.cog.build_embed(guild),
                    view=self
                )

        @discord.ui.button(label="Canal", style=discord.ButtonStyle.gray)
        async def canal_btn(self, interaction: discord.Interaction, button):

            view = discord.ui.View()
            select = discord.ui.ChannelSelect(
                channel_types=[discord.ChannelType.text]
            )

            async def select_callback(i: discord.Interaction):
                await i.response.defer(ephemeral=True)

                try:
                    # 🔥 forma correta (100% confiável)
                    channel_id = list(i.data["resolved"]["channels"].keys())[0]
                except:
                    # fallback
                    value = i.data["values"][0]
                    channel_id = value if isinstance(value, str) else value["id"]

                await set_cfg(
                    self.cog.bot,
                    i.guild.id,
                    {"channel_id": str(channel_id)}
                )

                await self.update_panel(i.guild)

                await i.followup.send("✅ Canal definido.", ephemeral=True)

            select.callback = select_callback
            view.add_item(select)

            await interaction.response.send_message(
                "Escolha o canal:",
                view=view,
                ephemeral=True
            )

        @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.blurple)
        async def toggle_btn(self, interaction: discord.Interaction, button):
            await interaction.response.defer()

            cfg = await get_cfg(self.cog.bot, interaction.guild.id)

            if not cfg.get("channel_id"):
                return await interaction.followup.send(
                    "❌ Defina o canal primeiro.",
                    ephemeral=True
                )

            await set_cfg(
                self.cog.bot,
                interaction.guild.id,
                {"ativo": not cfg.get("ativo", False)}
            )

            await self.update_panel(interaction.guild)

        @discord.ui.button(label="Nome", style=discord.ButtonStyle.gray)
        async def nome_btn(self, interaction, button):
            await interaction.response.send_modal(
                EasyThreads.InputModal(self.cog, "nome")
            )

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray)
        async def msg_btn(self, interaction, button):
            await interaction.response.send_modal(
                EasyThreads.InputModal(self.cog, "mensagem")
            )

    # ---------------- MODAL ----------------

    class InputModal(discord.ui.Modal):
        def __init__(self, cog, field):
            super().__init__(title=f"Editar {field}")
            self.cog = cog
            self.field = field

            self.input = discord.ui.TextInput(label="Valor", required=True)
            self.add_item(self.input)

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            await set_cfg(
                self.cog.bot,
                interaction.guild.id,
                {self.field: self.input.value}
            )

            view = EasyThreads.MainView(self.cog)
            await view.update_panel(interaction.guild)

            await interaction.followup.send("✅ Atualizado.", ephemeral=True)

    # ---------------- COMANDO ----------------

    @app_commands.command(name="autothread", description="Painel")
    async def autothread_cmd(self, interaction: discord.Interaction):

        await interaction.response.send_message(
            embed=await self.build_embed(interaction.guild)
        )

        msg = await interaction.original_response()

        await set_cfg(self.bot, interaction.guild.id, {
            "panel_message_id": str(msg.id)
        })

        await msg.edit(view=self.MainView(self))

    # ---------------- EVENTO ----------------

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return

        cfg = await get_cfg(self.bot, message.guild.id)

        if not cfg.get("ativo"):
            return

        if str(message.channel.id) != str(cfg.get("channel_id")):
            return

        try:
            nome = cfg.get("nome", "Thread de {user}")
            nome = nome.replace("{user}", message.author.name)

            thread = await message.create_thread(name=nome)

            msg = await thread.send(
                f"{message.author.mention} {cfg.get('mensagem', 'Bem-vindo!')}"
            )

            if cfg.get("pin"):
                await msg.pin()

        except Exception as e:
            print(f"Erro thread: {e}")


async def setup(bot):
    await bot.add_cog(EasyThreads(bot))
