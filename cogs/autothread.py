import discord
from discord.ext import commands
from discord import app_commands
import time

class AutoThread(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.cooldown = {}
        # Garante que bot.db exista como dicionário se não estiver definido
        if not hasattr(self.bot, 'db') or self.bot.db is None:
            self.bot.db = {}

    def get_db_collection(self):
        # Tenta pegar a coleção 'autothreads' ou retorna um mock vazio
        if isinstance(self.bot.db, dict):
            return self.bot.db.get("autothreads")
        return None

    # ========================
    # 🧠 CACHE E DB
    # ========================
    async def get_config(self, guild_id):
        if guild_id in self.cache:
            return self.cache[guild_id]

        collection = self.get_db_collection()
        if collection is None:
            return {}

        try:
            data = await collection.find_one({"guild_id": guild_id})
            self.cache[guild_id] = data
            return data
        except:
            return {}

    async def update_config(self, guild_id, data):
        collection = self.get_db_collection()
        if collection is not None:
            await collection.update_one(
                {"guild_id": guild_id},
                {"$set": data},
                upsert=True
            )
            new_data = await collection.find_one({"guild_id": guild_id})
            self.cache[guild_id] = new_data

    # ========================
    # 📊 EMBED STATUS
    # ========================
    async def build_embed(self, guild):
        config = await self.get_config(guild.id) or {}
        canal = guild.get_channel(config.get("channel_id", 0))
        status = "🟢 Ativo" if config.get("ativo") else "🔴 Desativado"
        canal_texto = canal.mention if canal else 'Não definido'

        embed = discord.Embed(title="🧵 Autothread Panel", color=discord.Color.blurple())
        embed.description = f"""
**Status:** {status}
**Canal:** {canal_texto}
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

        @discord.ui.button(label="Configurar", style=discord.ButtonStyle.blurple)
        async def config(self, interaction, button):
            # Menu de opções simplificado para evitar muitos modais
            await interaction.response.send_modal(AutoThread.NomeModal(self.cog))

    # --- Classes de Modal e Select permanecem iguais ---
    class CanalSelect(discord.ui.ChannelSelect):
        def __init__(self, cog):
            super().__init__(channel_types=[discord.ChannelType.text])
            self.cog = cog
        async def callback(self, interaction):
            await self.cog.update_config(interaction.guild.id, {"channel_id": self.values[0].id})
            embed = await self.cog.build_embed(interaction.guild)
            await interaction.response.edit_message(embed=embed)

    class NomeModal(discord.ui.Modal, title="Configurações"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
            self.nome_input = discord.ui.TextInput(label="Nome da thread", placeholder="Thread de {user}")
            self.add_item(self.nome_input)
        async def on_submit(self, interaction):
            await self.cog.update_config(interaction.guild.id, {"nome": self.nome_input.value})
            await interaction.response.send_message("Salvo!", ephemeral=True)

    @app_commands.command(name="autothread", description="Abrir painel")
    async def autothread(self, interaction: discord.Interaction):
        embed = await self.build_embed(interaction.guild)
        view = self.Panel(self)
        view.add_item(self.CanalSelect(self))
        await interaction.response.send_message(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        config = await self.get_config(message.guild.id)
        if not config or not config.get("ativo") or message.channel.id != config.get("channel_id"): return
        
        try:
            nome = config.get("nome", "Thread de {user}").replace("{user}", message.author.name)
            thread = await message.create_thread(name=nome, auto_archive_duration=1440)
            await thread.send(config.get("mensagem", "Thread criada."))
        except: pass

async def setup(bot):
    await bot.add_cog(AutoThread(bot))
        
