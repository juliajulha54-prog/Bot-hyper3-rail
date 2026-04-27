import discord
from discord.ext import commands
from discord import app_commands

# --- MOTOR DE DADOS À PROVA DE FALHAS ---
async def get_cfg(bot, guild_id):
    """Busca dados com fallback para dicionário vazio se o banco falhar."""
    if not hasattr(bot, 'db') or bot.db is None:
        print("⚠️ Erro: bot.db não foi inicializado no main.py")
        return {}

    try:
        col = bot.db["autothreads"]
        data = await col.find_one({"guild_id": str(guild_id)})
        return data if data else {}
    except Exception as e:
        print(f"❌ Erro ao ler DB: {e}")
        return {}


async def set_cfg(bot, guild_id, update_dict):
    """Salva dados garantindo a persistência."""
    if not hasattr(bot, 'db') or bot.db is None:
        print("❌ bot.db não encontrado")
        return

    try:
        col = bot.db["autothreads"]
        await col.update_one(
            {"guild_id": str(guild_id)},
            {"$set": update_dict},
            upsert=True
        )
    except Exception as e:
        print(f"❌ Erro ao salvar DB: {e}")


class EasyThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_status(self, value):
        return "🟢 `Ativado`" if value else "🔴 `Desativado`"

    async def build_embed(self, guild):
        cfg = await get_cfg(self.bot, guild.id)

        channel_id = cfg.get("channel_id")
        canal = guild.get_channel(int(channel_id)) if channel_id else None

        embed = discord.Embed(
            title="🧵 Painel Easy Threads",
            color=0x2b2d31
        )

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

        config_txt = (
            f"**Nome:** `{cfg.get('nome', 'Thread de {user}')}`\n"
            f"**Mensagem:** `{cfg.get('mensagem', 'Sua thread foi criada.')[:40]}...`"
        )

        embed.add_field(
            name="📝 Definições",
            value=config_txt,
            inline=False
        )

        opcoes = (
            f"Ignorar Bots: {self.get_status(cfg.get('ignorebots'))}\n"
            f"Fixar Mensagem: {self.get_status(cfg.get('pin'))}\n"
            f"Thread Privada: {self.get_status(cfg.get('private'))}"
        )

        embed.add_field(
            name="⚙️ Opções",
            value=opcoes,
            inline=False
        )

        embed.set_footer(text="Configure os campos antes de ativar o sistema.")
        return embed

    class MainView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="Canal", style=discord.ButtonStyle.gray, row=0)
        async def canal_btn(self, interaction: discord.Interaction, button):
            panel_message = interaction.message

            view = discord.ui.View(timeout=60)

            select = discord.ui.ChannelSelect(
                placeholder="Selecione o canal alvo...",
                channel_types=[discord.ChannelType.text]
            )

            async def select_callback(select_interaction: discord.Interaction):
                await select_interaction.response.defer(ephemeral=True)

                canal_id = str(select_interaction.data["values"][0])

                await set_cfg(
                    self.cog.bot,
                    select_interaction.guild.id,
                    {"channel_id": canal_id}
                )

                # Atualiza o painel corretamente
                embed = await self.cog.build_embed(select_interaction.guild)
                await panel_message.edit(embed=embed, view=self)

                await select_interaction.followup.send(
                    "✅ Canal definido com sucesso!",
                    ephemeral=True
                )

            select.callback = select_callback
            view.add_item(select)

            await interaction.response.send_message(
                "Escolha onde as threads serão criadas:",
                view=view,
                ephemeral=True
            )

        @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.blurple, row=0)
        async def toggle_btn(self, interaction: discord.Interaction, button):
            await interaction.response.defer()

            cfg = await get_cfg(self.cog.bot, interaction.guild.id)

            if not cfg.get("channel_id"):
                return await interaction.followup.send(
                    "❌ Você precisa definir o **Canal** antes!",
                    ephemeral=True
                )

            novo_status = not cfg.get("ativo", False)

            await set_cfg(
                self.cog.bot,
                interaction.guild.id,
                {"ativo": novo_status}
            )

            embed = await self.cog.build_embed(interaction.guild)
            await interaction.edit_original_response(embed=embed, view=self)

        @discord.ui.button(label="Nome", style=discord.ButtonStyle.gray, row=1)
        async def nome_btn(self, interaction: discord.Interaction, button):
            await interaction.response.send_modal(
                EasyThreads.InputModal(
                    self.cog,
                    "nome",
                    "Nome da Thread",
                    "{user} = Autor"
                )
            )

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray, row=1)
        async def msg_btn(self, interaction: discord.Interaction, button):
            await interaction.response.send_modal(
                EasyThreads.InputModal(
                    self.cog,
                    "mensagem",
                    "Mensagem Inicial",
                    "Texto da thread"
                )
            )

        @discord.ui.button(label="Privada", style=discord.ButtonStyle.gray, row=2)
        async def priv_btn(self, interaction: discord.Interaction, button):
            await interaction.response.defer()

            cfg = await get_cfg(self.cog.bot, interaction.guild.id)

            await set_cfg(
                self.cog.bot,
                interaction.guild.id,
                {"private": not cfg.get("private", False)}
            )

            embed = await self.cog.build_embed(interaction.guild)
            await interaction.edit_original_response(embed=embed, view=self)

        @discord.ui.button(label="Fixar Msg", style=discord.ButtonStyle.gray, row=2)
        async def pin_btn(self, interaction: discord.Interaction, button):
            await interaction.response.defer()

            cfg = await get_cfg(self.cog.bot, interaction.guild.id)

            await set_cfg(
                self.cog.bot,
                interaction.guild.id,
                {"pin": not cfg.get("pin", False)}
            )

            embed = await self.cog.build_embed(interaction.guild)
            await interaction.edit_original_response(embed=embed, view=self)

    class InputModal(discord.ui.Modal):
        def __init__(self, cog, field, title, hint):
            super().__init__(title=title)
            self.cog = cog
            self.field = field

            self.text_input = discord.ui.TextInput(
                label=hint,
                style=discord.TextStyle.paragraph,
                required=True
            )

            self.add_item(self.text_input)

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            await set_cfg(
                self.cog.bot,
                interaction.guild.id,
                {self.field: self.text_input.value}
            )

            await interaction.followup.send(
                f"✅ `{self.field}` atualizado com sucesso!",
                ephemeral=True
            )

    @app_commands.command(
        name="autothread",
        description="Painel Easy Threads v2"
    )
    async def autothread_cmd(self, interaction: discord.Interaction):
        embed = await self.build_embed(interaction.guild)

        await interaction.response.send_message(
            embed=embed,
            view=self.MainView(self)
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        cfg = await get_cfg(self.bot, message.guild.id)

        if cfg.get("ignorebots", True) and message.author.bot:
            return

        if not cfg.get("ativo"):
            return

        if str(message.channel.id) != str(cfg.get("channel_id")):
            return

        try:
            nome = cfg.get("nome", "Thread de {user}")
            nome = nome.replace("{user}", message.author.name)

            thread = await message.create_thread(
                name=nome,
                auto_archive_duration=1440
            )

            msg = await thread.send(
                f"{message.author.mention} {cfg.get('mensagem', 'Bem-vindo!')}"
            )

            if cfg.get("pin"):
                await msg.pin()

        except Exception as e:
            print(f"❌ Erro na thread: {e}")


async def setup(bot):
    await bot.add_cog(EasyThreads(bot))
