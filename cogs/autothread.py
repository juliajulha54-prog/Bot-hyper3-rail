import discord
from discord.ext import commands
from discord import app_commands

# --- UTILITÁRIOS DE BANCO ---
async def get_cfg(bot, gid):
    if not hasattr(bot, 'db') or bot.db is None: return {}
    col = bot.db["autothreads"]
    return await col.find_one({"guild_id": gid}) or {}

async def set_cfg(bot, gid, data):
    if not hasattr(bot, 'db') or bot.db is None: return
    col = bot.db["autothreads"]
    await col.update_one({"guild_id": gid}, {"$set": data}, upsert=True)

class AutoThreadEasy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def build_embed(self, guild):
        config = await get_cfg(self.bot, guild.id)
        canal = guild.get_channel(config.get("channel_id", 0))
        
        embed = discord.Embed(title="🧵 Configurações de Auto-Thread", color=0x2b2d31)
        status = "✅ Ativo" if config.get("ativo") else "❌ Desativado"
        
        embed.add_field(name="Canal", value=canal.mention if canal else "Não definido", inline=True)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Nome", value=f"`{config.get('nome', 'Thread de {user}')}`", inline=False)
        
        # Resumo das opções extras
        extras = []
        if config.get("ignorebots"): extras.append("🤖 Ignorando Bots")
        if config.get("pin"): extras.append("📌 Fixando Mensagem")
        if config.get("private"): extras.append("🔒 Privada")
        
        embed.set_footer(text="Ajuste as opções nos botões abaixo")
        return embed

    # --- VIEW IGUAL AO VÍDEO ---
    class EasyView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        # FILEIRA 0
        @discord.ui.button(label="Canal", style=discord.ButtonStyle.gray, row=0)
        async def canal_btn(self, i, b):
            await i.response.send_message("Use o seletor abaixo para definir o canal:", view=AutoThreadEasy.SelectChannelView(self.cog), ephemeral=True)

        @discord.ui.button(label="Ativar/Desativar", style=discord.ButtonStyle.gray, row=0)
        async def toggle_btn(self, i, b):
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            await set_cfg(self.cog.bot, i.guild.id, {"ativo": not cfg.get("ativo", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Nome", style=discord.ButtonStyle.gray, row=0)
        async def nome_btn(self, i, b):
            await i.response.send_modal(AutoThreadEasy.ConfigModal(self.cog, "nome", "Nome da Thread"))

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray, row=0)
        async def msg_btn(self, i, b):
            await i.response.send_modal(AutoThreadEasy.ConfigModal(self.cog, "mensagem", "Mensagem Inicial"))

        # FILEIRA 1
        @discord.ui.button(label="Delay", style=discord.ButtonStyle.gray, row=1)
        async def delay_btn(self, i, b):
            await i.response.send_message("Função de Delay selecionada.", ephemeral=True)

        @discord.ui.button(label="Ignorar Bots", style=discord.ButtonStyle.gray, row=1)
        async def bots_btn(self, i, b):
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            await set_cfg(self.cog.bot, i.guild.id, {"ignorebots": not cfg.get("ignorebots", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Fixar Msg", style=discord.ButtonStyle.gray, row=1)
        async def pin_btn(self, i, b):
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            await set_cfg(self.cog.bot, i.guild.id, {"pin": not cfg.get("pin", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Privada", style=discord.ButtonStyle.gray, row=1)
        async def private_btn(self, i, b):
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            await set_cfg(self.cog.bot, i.guild.id, {"private": not cfg.get("private", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

    # --- COMPONENTES AUXILIARES ---
    class SelectChannelView(discord.ui.View):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
        @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Selecione o canal...")
        async def select_callback(self, i, s):
            await set_cfg(self.cog.bot, i.guild.id, {"channel_id": s.values[0].id})
            await i.response.send_message(f"✅ Canal alterado para {s.values[0].mention}!", ephemeral=True)

    class ConfigModal(discord.ui.Modal):
        def __init__(self, cog, chave, titulo):
            super().__init__(title=titulo)
            self.cog, self.chave = cog, chave
            self.input = discord.ui.TextInput(label=titulo, style=discord.TextStyle.paragraph)
            self.add_item(self.input)
        async def on_submit(self, i):
            await set_cfg(self.cog.bot, i.guild.id, {self.chave: self.input.value})
            await i.response.send_message(f"✅ {self.chave.capitalize()} atualizado!", ephemeral=True)
            await i.message.edit(embed=await self.cog.build_embed(i.guild))

    # --- COMANDO E EVENTO ---
    @app_commands.command(name="autothread", description="Painel estilo Easy Threads")
    async def autothread(self, i: discord.Interaction):
        await i.response.send_message(embed=await self.build_embed(i.guild), view=self.EasyView(self))

    @commands.Cog.listener()
    async def on_message(self, m):
        if m.author.bot or not m.guild: return
        cfg = await get_cfg(self.bot, m.guild.id)
        if not cfg.get("ativo") or m.channel.id != cfg.get("channel_id"): return
        
        if cfg.get("ignorebots") and m.author.bot: return

        try:
            nome = cfg.get("nome", "Thread de {user}").replace("{user}", m.author.name)
            thread = await m.create_thread(name=nome, auto_archive_duration=1440)
            msg = await thread.send(f"{m.author.mention} {cfg.get('mensagem', 'Thread criada!')}")
            if cfg.get("pin"): await msg.pin()
        except Exception as e: print(f"Erro: {e}")

async def setup(bot):
    await bot.add_cog(AutoThreadEasy(bot))
        
