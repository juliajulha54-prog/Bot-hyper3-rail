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
                f"Nome: `{cfg.get('nome', 'Thread de {user}')}`\n"
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
        def __init__(self, cog, panel_message):
            super().__init__(timeout=None)
            self.cog = cog
            self.panel_message = panel_message

        @discord.ui.button(label="Canal", style=discord.ButtonStyle.gray)
        async def canal_btn(self, interaction: discord.Interaction, button):

            view = discord.ui.View()
            select = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text])

            async def select_callback(i: discord.Interaction):
                await i.response.defer(ephemeral=True)

                channel_id = i.data["values"][0]

                await set_cfg(
                    self.cog.bot,
                    i.guild.id,
                    {"channel_id": str(channel_id)}
                )

                # 🔥 ATUALIZA O PAINEL CORRETO
                await self.panel_message.edit(
                    embed=await self.cog.build_embed(i.guild),
                    view=self
                )

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

            await self.panel_message.edit(
                embed=await self.cog.build_embed(interaction.guild),
                view=self
            )

        @discord.ui.button(label="Nome", style=discord.ButtonStyle.gray)
        async def nome_btn(self, interaction, button):
            await interaction.response.send_modal(
                EasyThreads.InputModal(self.cog, "nome", self.panel_message)
            )

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray)
        async def msg_btn(self, interaction, button):
            await interaction.response.send_modal(
                EasyThreads.InputModal(self.cog, "mensagem", self.panel_message)
            )

    # ---------------- MODAL ----------------

    class InputModal(discord.ui.Modal):
        def __init__(self, cog, field, panel_message):
            super().__init__(title=f"Editar {field}")
            self.cog = cog
            self.field = field
            self.panel_message = panel_message

            self.input = discord.ui.TextInput(label="Valor", required=True)
            self.add_item(self.input)

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            await set_cfg(
                self.cog.bot,
                interaction.guild.id,
                {self.field: self.input.value}
            )

            await self.panel_message.edit(
                embed=await self.cog.build_embed(interaction.guild),
                view=EasyThreads.MainView(self.cog, self.panel_message)
            )

            await interaction.followup.send("✅ Atualizado.", ephemeral=True)

    # ---------------- COMANDO ----------------

    @app_commands.command(name="autothread", description="Painel")
    async def autothread_cmd(self, interaction: discord.Interaction):

        await interaction.response.send_message(
            embed=await self.build_embed(interaction.guild)
        )

        # 🔥 pega a mensagem REAL
        msg = await interaction.original_response()

        view = self.MainView(self, msg)
        await msg.edit(view=view)

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
