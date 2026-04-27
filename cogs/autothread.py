import discord
from discord.ext import commands
from discord import app_commands
import time

class AutoThread(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.cooldown = {}
        # Garante que o db exista como dicionário para evitar o erro de inicialização
        if not hasattr(self.bot, 'db'):
            self.bot.db = {}

    def get_collection(self):
        # Acesso seguro à coleção
        if isinstance(self.bot.db, dict):
            return self.bot.db.get("autothreads")
        return None

    async def get_config(self, guild_id):
        if guild_id in self.cache: return self.cache[guild_id]
        col = self.get_collection()
        if col is None: return {}
        data = await col.find_one({"guild_id": guild_id})
        self.cache[guild_id] = data
        return data

    async def update_config(self, guild_id, data):
        col = self.get_collection()
        if col is not None:
            await col.update_one({"guild_id": guild_id}, {"$set": data}, upsert=True)
            self.cache[guild_id] = await col.find_one({"guild_id": guild_id})

    async def build_embed(self, guild):
        config = await self.get_config(guild.id) or {}
        canal = guild.get_channel(config.get("channel_id", 0))
        status = "🟢 Ativo" if config.get("ativo") else "🔴 Desativado"
        embed = discord.Embed(title="🧵 Autothread Panel", color=discord.Color.blurple())
        embed.description = f"**Status:** {status}\n**Canal:** {canal.mention if canal else 'Não definido'}\n**Nome:** `{config.get('nome', 'Thread de {user}')}`\n**Mensagem:** `{config.get('mensagem', 'Padrão')[:50]}`\n**Fixar:** {'Sim' if config.get('fixar', True) else 'Não'}"
        return embed

    # --- VIEWS E MODALS ---
    class Panel(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="Ativar", style=discord.ButtonStyle.green)
        async def ativar(self, i, b):
            await self.cog.update_config(i.guild.id, {"ativo": True})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Desativar", style=discord.ButtonStyle.red)
        async def desativar(self, i, b):
            await self.cog.update_config(i.guild.id, {"ativo": False})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Nome", style=discord.ButtonStyle.blurple)
        async def nome(self, i, b):
            await i.response.send_modal(AutoThread.NomeModal(self.cog))

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray)
        async def msg(self, i, b):
            await i.response.send_modal(AutoThread.MsgModal(self.cog))

    class CanalSelect(discord.ui.ChannelSelect):
        def __init__(self, cog):
            super().__init__(channel_types=[discord.ChannelType.text], placeholder="Selecione o canal...")
            self.cog = cog
        async def callback(self, i):
            await self.cog.update_config(i.guild.id, {"channel_id": self.values[0].id})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

    class NomeModal(discord.ui.Modal, title="Configurar Nome"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
            self.input = discord.ui.TextInput(label="Novo Nome", placeholder="Thread de {user}")
            self.add_item(self.input)
        async def on_submit(self, i):
            await self.cog.update_config(i.guild.id, {"nome": self.input.value})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

    class MsgModal(discord.ui.Modal, title="Configurar Mensagem"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
            self.input = discord.ui.TextInput(label="Mensagem", style=discord.TextStyle.paragraph)
            self.add_item(self.input)
        async def on_submit(self, i):
            await self.cog.update_config(i.guild.id, {"mensagem": self.input.value})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

    # --- COMANDO ---
    @app_commands.command(name="autothread")
    async def autothread(self, i: discord.Interaction):
        view = self.Panel(self)
        view.add_item(self.CanalSelect(self))
        await i.response.send_message(embed=await self.build_embed(i.guild), view=view)

    @commands.Cog.listener()
    async def on_message(self, m):
        if m.author.bot or not m.guild: return
        config = await self.get_config(m.guild.id)
        if not config or not config.get("ativo") or m.channel.id != config.get("channel_id"): return
        
        # Lógica de criação de thread
        try:
            nome = config.get("nome", "Thread de {user}").replace("{user}", m.author.name)
            thread = await m.create_thread(name=nome, auto_archive_duration=1440)
            await thread.send(config.get("mensagem", "Thread criada."))
        except Exception as e: print(e)

async def setup(bot):
    await bot.add_cog(AutoThread(bot))
        
