import discord
from discord.ext import commands
from discord import app_commands
import asyncio

# --- MOTOR DE BANCO DE DADOS SEGURO ---
async def get_data(bot, guild_id):
    """Garante que sempre retorne um dicionário, evitando NoneType errors."""
    if not hasattr(bot, 'db') or bot.db is None:
        return {}
    try:
        col = bot.db["autothreads"]
        data = await col.find_one({"guild_id": guild_id})
        return data if data else {}
    except Exception as e:
        print(f"Erro ao ler DB: {e}")
        return {}

async def update_data(bot, guild_id, update_dict):
    """Atualiza o banco de forma atômica."""
    if not hasattr(bot, 'db') or bot.db is None:
        return
    try:
        col = bot.db["autothreads"]
        await col.update_one({"guild_id": guild_id}, {"$set": update_dict}, upsert=True)
    except Exception as e:
        print(f"Erro ao salvar DB: {e}")

class EasyThreadsClone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def status(self, val):
        return "🟢 `Ativado`" if val else "🔴 `Desativado`"

    # --- CONSTRUTOR DO PAINEL (VISUAL IDENTICO AO VÍDEO) ---
    async def make_panel(self, guild):
        cfg = await get_data(self.bot, guild.id)
        canal = guild.get_channel(cfg.get("channel_id", 0))
        
        embed = discord.Embed(title="🧵 Configuração Autothread", color=0x2b2d31)
        embed.add_field(name="📍 Canal Alvo", value=canal.mention if canal else "❌ `Não definido`", inline=True)
        embed.add_field(name="Status", value=self.status(cfg.get("ativo")), inline=True)
        
        txt = (f"**Nome:** `{cfg.get('nome', 'Thread de {user}')}`\n"
               f"**Mensagem:** `{cfg.get('mensagem', 'Padrão')[:30]}...`\n"
               f"**Delay:** `{cfg.get('delay', 0)}s` | **Cooldown:** `{cfg.get('cooldown', 0)}s`")
        embed.add_field(name="📝 Definições de Texto", value=txt, inline=False)

        extras = (f"Ignorar Bots: {self.status(cfg.get('ignorebots'))}\n"
                  f"Fixar Mensagem: {self.status(cfg.get('pin'))}\n"
                  f"Thread Privada: {self.status(cfg.get('private'))}\n"
                  f"Bloquear Convites: {self.status(cfg.get('block_invites'))}")
        embed.add_field(name="⚙️ Opções Adicionais", value=extras, inline=False)
        embed.set_footer(text="Easy Threads System • Configuração em tempo real")
        return embed

    # --- VIEW PRINCIPAL ---
    class MainView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        # --- CANAL ---
        @discord.ui.button(label="Canal", style=discord.ButtonStyle.gray, row=0)
        async def set_channel(self, i, b):
            view = discord.ui.View()
            select = discord.ui.ChannelSelect(placeholder="Selecione o canal...", channel_types=[discord.ChannelType.text])
            
            async def cb(interaction):
                await interaction.response.defer(ephemeral=True) # Evita "Interação falhou"
                await update_data(self.cog.bot, i.guild.id, {"channel_id": select.values[0].id})
                await i.edit_original_response(embed=await self.cog.make_panel(i.guild))
                await interaction.followup.send("✅ Canal definido!", ephemeral=True)
            
            select.callback = cb
            view.add_item(select)
            await i.response.send_message("Onde as threads serão criadas?", view=view, ephemeral=True)

        # --- ATIVAR/DESATIVAR ---
        @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.blurple, row=0)
        async def toggle(self, i, b):
            cfg = await get_data(self.cog.bot, i.guild.id)
            if not cfg.get("channel_id"):
                return await i.response.send_message("❌ Defina o **Canal** primeiro!", ephemeral=True)
            
            await update_data(self.cog.bot, i.guild.id, {"ativo": not cfg.get("ativo", False)})
            await i.response.edit_message(embed=await self.cog.make_panel(i.guild))

        # --- TEXTOS ---
        @discord.ui.button(label="Nome", style=discord.ButtonStyle.gray, row=1)
        async def set_name(self, i, b):
            await i.response.send_modal(EasyThreadsClone.TextModal(self.cog, "nome", "Nome da Thread", "{user} = Autor"))

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray, row=1)
        async def set_msg(self, i, b):
            await i.response.send_modal(EasyThreadsClone.TextModal(self.cog, "mensagem", "Mensagem Inicial", "Texto dentro da thread"))

        # --- SWITCHES ---
        @discord.ui.button(label="Ignorar Bots", style=discord.ButtonStyle.gray, row=2)
        async def t_bots(self, i, b):
            cfg = await get_data(self.cog.bot, i.guild.id)
            await update_data(self.cog.bot, i.guild.id, {"ignorebots": not cfg.get("ignorebots", False)})
            await i.response.edit_message(embed=await self.cog.make_panel(i.guild))

        @discord.ui.button(label="Fixar Msg", style=discord.ButtonStyle.gray, row=2)
        async def t_pin(self, i, b):
            cfg = await get_data(self.cog.bot, i.guild.id)
            await update_data(self.cog.bot, i.guild.id, {"pin": not cfg.get("pin", False)})
            await i.response.edit_message(embed=await self.cog.make_panel(i.guild))

        @discord.ui.button(label="Privada", style=discord.ButtonStyle.gray, row=2)
        async def t_priv(self, i, b):
            cfg = await get_data(self.cog.bot, i.guild.id)
            await update_data(self.cog.bot, i.guild.id, {"private": not cfg.get("private", False)})
            await i.response.edit_message(embed=await self.cog.make_panel(i.guild))

    # --- MODAL CORRIGIDO (NÃO DÁ "ALGO DEU ERRADO") ---
    class TextModal(discord.ui.Modal):
        def __init__(self, cog, key, title, hint):
            super().__init__(title=title)
            self.cog, self.key = cog, key
            self.inp = discord.ui.TextInput(label=hint, style=discord.TextStyle.paragraph, required=True)
            self.add_item(self.inp)

        async def on_submit(self, interaction):
            # 1. Avisa o Discord que recebeu
            await interaction.response.defer(ephemeral=True)
            # 2. Salva no banco
            await update_data(self.cog.bot, interaction.guild.id, {self.key: self.inp.value})
            # 3. Atualiza o painel principal (através da mensagem original do modal)
            try:
                await interaction.message.edit(embed=await self.cog.make_panel(interaction.guild))
                await interaction.followup.send(f"✅ `{self.key}` atualizado!", ephemeral=True)
            except:
                await interaction.followup.send("✅ Salvo! (Atualize o painel com /autothread)", ephemeral=True)

    # --- COMANDO ---
    @app_commands.command(name="autothread", description="Painel Easy Threads")
    async def autothread(self, i: discord.Interaction):
        await i.response.send_message(embed=await self.make_panel(i.guild), view=self.MainView(self))

    # --- SISTEMA DE CRIAÇÃO ---
    @commands.Cog.listener()
    async def on_message(self, m):
        if not m.guild or m.author.bot: return
        cfg = await get_data(self.bot, m.guild.id)
        if not cfg.get("ativo") or m.channel.id != cfg.get("channel_id"): return
        
        if cfg.get("ignorebots") and m.author.bot: return

        try:
            nome = cfg.get("nome", "Thread de {user}").replace("{user}", m.author.name)
            
            # Delay de criação se configurado
            delay = cfg.get("delay", 0)
            if delay > 0: await asyncio.sleep(delay)

            thread = await m.create_thread(name=nome, auto_archive_duration=1440)
            
            msg = await thread.send(f"{m.author.mention} {cfg.get('mensagem', 'Thread criada!')}")
            if cfg.get("pin"): await msg.pin()
        except Exception as e:
            print(f"Erro ao criar thread: {e}")

async def setup(bot):
    await bot.add_cog(EasyThreadsClone(bot))
        
