import discord
from discord.ext import commands
from discord import app_commands
import time

class AutoThread(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Removi a definição direta de self.db aqui para evitar o erro de NoneType
        self.cache = {}
        self.cooldown = {}

    # Propriedade para pegar o banco de dados sempre atualizado da main
    @property
    def db(self):
        return self.bot.db["autothreads"]

    # ========================
    # 🧠 CACHE
    # ========================
    async def get_config(self, guild_id):
        if guild_id in self.cache:
            return self.cache[guild_id]

        if self.bot.db is None:
            return None

        data = await self.db.find_one({"guild_id": guild_id})
        self.cache[guild_id] = data
        return data

    async def update_config(self, guild_id, data):
        await self.db.update_one(
            {"guild_id": guild_id},
            {"$set": data},
            upsert=True
        )
        # Atualiza o cache após salvar
        new_data = await self.db.find_one({"guild_id": guild_id})
        self.cache[guild_id] = new_data

    # ========================
    # 📊 EMBED STATUS
    # ========================
    async def build_embed(self, guild):
        config = await self.get_config(guild.id) or {}

        canal_id = config.get("channel_id", 0)
        canal = guild.get_channel(canal_id)
        status = "🟢 Ativo" if config.get("ativo") else "🔴 Desativado"

        embed = discord.Embed(
            title="🧵 Autothread Panel",
            color=discord.Color.blurple()
        )
        embed.description = f"""
**Status:** {status}
**Canal:** {canal.mention if canal else 'Não definido'}
**Nome:** `{config.get('nome', 'Thread de {user}')}`
**Mensagem:** `{config.get('mensagem', 'Padrão')[:50]}`
**Fixar:** {'Sim' if config.get('fixar', True) else 'Não'}
"""
        return embed

    # ========================
    # 🎛️ VIEW & MODALS
    # ========================
    class Panel(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="Ativar", style=discord.ButtonStyle.green)
        async def ativar(self, interaction, button):
            await self.cog.update_config(interaction.guild.id, {"ativo": True})
            embed = await self.cog.build_embed(interaction.guild)
            await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(label="Desativar", style=discord.ButtonStyle.red)
        async def desativar(self, interaction, button):
            await self.cog.update_config(interaction.guild.id, {"ativo": False})
            embed = await self.cog.build_embed(interaction.guild)
            await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(label="Nome", style=discord.ButtonStyle.blurple)
        async def nome(self, interaction, button):
            await interaction.response.send_modal(AutoThread.NomeModal(self.cog))

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray)
        async def mensagem(self, interaction, button):
            await interaction.response.send_modal(AutoThread.MsgModal(self.cog))

        @discord.ui.button(label="Fixar ON/OFF", style=discord.ButtonStyle.gray)
        async def fixar(self, interaction, button):
            config = await self.cog.get_config(interaction.guild.id) or {}
            novo = not config.get("fixar", True)
            await self.cog.update_config(interaction.guild.id, {"fixar": novo})
            embed = await self.cog.build_embed(interaction.guild)
            await interaction.response.edit_message(embed=embed, view=self)

    class CanalSelect(discord.ui.ChannelSelect):
        def __init__(self, cog):
            super().__init__(channel_types=[discord.ChannelType.text])
            self.cog = cog

        async def callback(self, interaction):
            canal = self.values[0]
            await self.cog.update_config(interaction.guild.id, {"channel_id": canal.id})
            embed = await self.cog.build_embed(interaction.guild)
            view = AutoThread.Panel(self.cog)
            view.add_item(AutoThread.CanalSelect(self.cog))
            await interaction.response.edit_message(embed=embed, view=view)

    class NomeModal(discord.ui.Modal, title="Nome da Thread"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
            self.nome_input = discord.ui.TextInput(label="Nome da thread", placeholder="Thread de {user}")
            self.add_item(self.nome_input)

        async def on_submit(self, interaction):
            await self.cog.update_config(interaction.guild.id, {"nome": self.nome_input.value})
            embed = await self.cog.build_embed(interaction.guild)
            view = AutoThread.Panel(self.cog)
            view.add_item(AutoThread.CanalSelect(self.cog))
            await interaction.response.edit_message(embed=embed, view=view)

    class MsgModal(discord.ui.Modal, title="Mensagem da Thread"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
            self.msg_input = discord.ui.TextInput(label="Mensagem da thread", style=discord.TextStyle.paragraph)
            self.add_item(self.msg_input)

        async def on_submit(self, interaction):
            await self.cog.update_config(interaction.guild.id, {"mensagem": self.msg_input.value})
            embed = await self.cog.build_embed(interaction.guild)
            view = AutoThread.Panel(self.cog)
            view.add_item(AutoThread.CanalSelect(self.cog))
            await interaction.response.edit_message(embed=embed, view=view)

    # ========================
    # 🚀 SLASH COMMAND
    # ========================
    @app_commands.command(name="autothread", description="Abrir painel de configuração")
    async def autothread(self, interaction: discord.Interaction):
        if self.bot.db is None:
            return await interaction.response.send_message("❌ Banco de dados offline.", ephemeral=True)
            
        embed = await self.build_embed(interaction.guild)
        view = self.Panel(self)
        view.add_item(self.CanalSelect(self))
        await interaction.response.send_message(embed=embed, view=view)

    # ========================
    # 🧵 EVENTO DE CRIAÇÃO
    # ========================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        config = await self.get_config(message.guild.id)
        if not config or not config.get("ativo"):
            return

        if message.channel.id != config.get("channel_id"):
            return

        # Cooldown simples para evitar spam
        now = time.time()
        if now - self.cooldown.get(message.author.id, 0) < 5:
            return
        self.cooldown[message.author.id] = now

        if isinstance(message.channel, discord.Thread):
            return

        try:
            nome_base = config.get("nome", "Thread de {user}")
            nome = nome_base.replace("{user}", message.author.name).replace("{msg}", message.content[:20])

            thread = await message.create_thread(name=nome, auto_archive_duration=1440)
            msg = await thread.send(config.get("mensagem", "Thread criada."))

            if config.get("fixar", True):
                try:
                    await msg.pin()
                except:
                    pass
        except Exception as e:
            print(f"❌ Erro ao criar thread: {e}")

async def setup(bot):
    await bot.add_cog(AutoThread(bot))
