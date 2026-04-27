import discord
from discord.ext import commands
from discord import app_commands

# --- HELPERS DE BANCO DE DADOS (SEGURANÇA TOTAL) ---
async def get_cfg(bot, gid):
    if not hasattr(bot, 'db') or bot.db is None: return {}
    try:
        col = bot.db["autothreads"]
        data = await col.find_one({"guild_id": gid})
        return data or {}
    except: return {}

async def set_cfg(bot, gid, data):
    if not hasattr(bot, 'db') or bot.db is None: return
    col = bot.db["autothreads"]
    await col.update_one({"guild_id": gid}, {"$set": data}, upsert=True)

class AutoThreadEasy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_status_emoji(self, value):
        return "🟢 `Ativado`" if value else "🔴 `Desativado`"

    async def build_embed(self, guild):
        cfg = await get_cfg(self.bot, guild.id)
        canal = guild.get_channel(cfg.get("channel_id", 0))
        
        embed = discord.Embed(title="🧵 Configuração Autothread", color=0x2b2d31)
        
        # Seção Principal (Obrigatórios)
        embed.add_field(name="📍 Canal Alvo", value=canal.mention if canal else "❌ `Não definido`", inline=True)
        embed.add_field(name="Status", value=self.get_status_emoji(cfg.get("ativo")), inline=True)
        
        # Categorias de Configuração (Igual ao vídeo)
        config_text = (
            f"**Nome:** `{cfg.get('nome', 'Thread de {user}')}`\n"
            f"**Mensagem:** `{cfg.get('mensagem', 'Padrão')[:30]}...`\n"
            f"**Delay:** `{cfg.get('delay', 0)}s` | **Cooldown:** `{cfg.get('cooldown', 0)}s`"
        )
        embed.add_field(name="📝 Definições de Texto", value=config_text, inline=False)

        # Switche (Ativado/Desativado)
        extras = (
            f"Ignorar Bots: {self.get_status_emoji(cfg.get('ignorebots'))}\n"
            f"Fixar Mensagem: {self.get_status_emoji(cfg.get('pin'))}\n"
            f"Thread Privada: {self.get_status_emoji(cfg.get('private'))}\n"
            f"Bloquear Convites: {self.get_status_emoji(cfg.get('block_invites'))}"
        )
        embed.add_field(name="⚙️ Opções Adicionais", value=extras, inline=False)
        
        embed.set_footer(text="Easy Threads Clone • Use os botões para configurar")
        return embed

    # --- VIEW COM TODAS AS CATEGORIAS DO VÍDEO ---
    class EasyView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        # FILEIRA 0: OBRIGATÓRIOS E ATIVAÇÃO
        @discord.ui.button(label="Canal", style=discord.ButtonStyle.gray, row=0)
        async def canal_btn(self, i, b):
            view = discord.ui.View()
            select = discord.ui.ChannelSelect(placeholder="Selecione o canal alvo...")
            async def callback(interaction):
                await set_cfg(self.cog.bot, i.guild.id, {"channel_id": select.values[0].id})
                await interaction.response.send_message(f"✅ Canal {select.values[0].mention} definido!", ephemeral=True)
                await i.edit_original_response(embed=await self.cog.build_embed(i.guild))
            select.callback = callback
            view.add_item(select)
            await i.response.send_message("Selecione onde as threads serão criadas:", view=view, ephemeral=True)

        @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.blurple, row=0)
        async def toggle_btn(self, i, b):
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            # VALIDAÇÃO: Não deixa ativar sem canal
            if not cfg.get("channel_id"):
                return await i.response.send_message("❌ **Erro:** Você precisa definir um **Canal** antes de ativar!", ephemeral=True)
            
            await set_cfg(self.cog.bot, i.guild.id, {"ativo": not cfg.get("ativo", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        # FILEIRA 1: TEXTOS (MODAIS)
        @discord.ui.button(label="Nome", style=discord.ButtonStyle.gray, row=1)
        async def nome_btn(self, i, b):
            modal = AutoThreadEasy.ConfigModal(self.cog, "nome", "Nome da Thread", "{user} = Nome do Usuário")
            await i.response.send_modal(modal)

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray, row=1)
        async def msg_btn(self, i, b):
            modal = AutoThreadEasy.ConfigModal(self.cog, "mensagem", "Mensagem Inicial", "Texto que o bot enviará na thread")
            await i.response.send_modal(modal)

        # FILEIRA 2: OPÇÕES (SÓ CLICAR E MUDA O STATUS)
        @discord.ui.button(label="Ignorar Bots", style=discord.ButtonStyle.gray, row=2)
        async def bots_btn(self, i, b):
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            await set_cfg(self.cog.bot, i.guild.id, {"ignorebots": not cfg.get("ignorebots", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Fixar Msg", style=discord.ButtonStyle.gray, row=2)
        async def pin_btn(self, i, b):
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            await set_cfg(self.cog.bot, i.guild.id, {"pin": not cfg.get("pin", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Privada", style=discord.ButtonStyle.gray, row=2)
        async def private_btn(self, i, b):
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            await set_cfg(self.cog.bot, i.guild.id, {"private": not cfg.get("private", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

    # --- MODAL PARA ENTRADA DE TEXTO ---
    class ConfigModal(discord.ui.Modal):
        def __init__(self, cog, chave, titulo, desc):
            super().__init__(title=titulo)
            self.cog, self.chave = cog, chave
            self.input = discord.ui.TextInput(label=desc, style=discord.TextStyle.paragraph, required=True)
            self.add_item(self.input)

        async def on_submit(self, i):
            await set_cfg(self.cog.bot, i.guild.id, {self.chave: self.input.value})
            await i.response.send_message(f"✅ `{self.chave}` atualizado!", ephemeral=True)
            await i.message.edit(embed=await self.cog.build_embed(i.guild))

    # --- COMANDO ---
    @app_commands.command(name="autothread", description="Painel completo estilo Easy Threads")
    async def autothread_cmd(self, i: discord.Interaction):
        await i.response.send_message(embed=await self.build_embed(i.guild), view=self.EasyView(self))

    # --- LOGICA DE CRIAÇÃO ---
    @commands.Cog.listener()
    async def on_message(self, m):
        if not m.guild or m.author.bot: return
        cfg = await get_cfg(self.bot, m.guild.id)
        if not cfg.get("ativo") or m.channel.id != cfg.get("channel_id"): return
        
        # Respeita a opção de ignorar bots
        if cfg.get("ignorebots") and m.author.bot: return

        try:
            nome = cfg.get("nome", "Thread de {user}").replace("{user}", m.author.name)
            # Cria a thread (privada ou pública conforme config)
            tipo = discord.ChannelType.private_thread if cfg.get("private") else discord.ChannelType.public_thread
            
            thread = await m.create_thread(name=nome, auto_archive_duration=1440)
            
            msg_content = cfg.get("mensagem", "Sua thread foi criada.")
            msg = await thread.send(f"{m.author.mention} {msg_content}")
            
            if cfg.get("pin"): await msg.pin()
        except Exception as e: print(f"Erro ao criar thread: {e}")

async def setup(bot):
    await bot.add_cog(AutoThreadEasy(bot))
        
