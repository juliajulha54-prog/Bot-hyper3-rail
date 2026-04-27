import discord
from discord.ext import commands
from discord import app_commands
import asyncio

# --- MOTOR DE DADOS À PROVA DE FALHAS ---
async def get_cfg(bot, guild_id):
    """Busca dados com fallback para dicionário vazio se o banco falhar."""
    if not hasattr(bot, 'db') or bot.db is None:
        print("⚠️ Erro: bot.db não foi inicializado no main.py")
        return {}
    try:
        # Usamos String para o ID para garantir compatibilidade no MongoDB
        col = bot.db["autothreads"]
        data = await col.find_one({"guild_id": str(guild_id)})
        return data if data else {}
    except Exception as e:
        print(f"❌ Erro ao ler DB: {e}")
        return {}

async def set_cfg(bot, guild_id, update_dict):
    """Salva dados garantindo a persistência."""
    if not hasattr(bot, 'db') or bot.db is None:
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
        canal = guild.get_channel(int(cfg.get("channel_id", 0)))
        
        embed = discord.Embed(title="🧵 Painel Easy Threads", color=0x2b2d31)
        
        # Seção 1: Status e Canal
        embed.add_field(name="📍 Canal Alvo", value=canal.mention if canal else "❌ `Não definido`", inline=True)
        embed.add_field(name="Status Geral", value=self.get_status(cfg.get("ativo")), inline=True)
        
        # Seção 2: Textos
        config_txt = (
            f"**Nome:** `{cfg.get('nome', 'Thread de {user}')}`\n"
            f"**Mensagem:** `{cfg.get('mensagem', 'Sua thread foi criada.')[:40]}...`"
        )
        embed.add_field(name="📝 Definições", value=config_txt, inline=False)

        # Seção 3: Adicionais
        opcoes = (
            f"Ignorar Bots: {self.get_status(cfg.get('ignorebots'))}\n"
            f"Fixar Mensagem: {self.get_status(cfg.get('pin'))}\n"
            f"Thread Privada: {self.get_status(cfg.get('private'))}"
        )
        embed.add_field(name="⚙️ Opções", value=opcoes, inline=False)
        
        embed.set_footer(text="Configure os campos antes de ativar o sistema.")
        return embed

    # --- VIEW COM INTERAÇÕES PROTEGIDAS ---
    class MainView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="Canal", style=discord.ButtonStyle.gray, row=0)
        async def canal_btn(self, i, b):
            # Envia o seletor em uma mensagem separada para não bugar o painel
            view = discord.ui.View()
            select = discord.ui.ChannelSelect(placeholder="Selecione o canal alvo...", channel_types=[discord.ChannelType.text])
            
            async def select_callback(it):
                await it.response.defer(ephemeral=True) # Essencial para Railway
                canal_id = it.data['values'][0]
                await set_cfg(self.cog.bot, it.guild.id, {"channel_id": canal_id})
                # Atualiza o painel principal
                await i.edit_original_response(embed=await self.cog.build_embed(it.guild))
                await it.followup.send(f"✅ Canal definido com sucesso!", ephemeral=True)

            select.callback = select_callback
            view.add_item(select)
            await i.response.send_message("Escolha onde as threads serão criadas:", view=view, ephemeral=True)

        @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.blurple, row=0)
        async def toggle_btn(self, i, b):
            await i.response.defer() # Segura a interação
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            
            if not cfg.get("channel_id"):
                return await i.followup.send("❌ Você precisa definir o **Canal** antes!", ephemeral=True)
            
            novo_status = not cfg.get("ativo", False)
            await set_cfg(self.cog.bot, i.guild.id, {"ativo": novo_status})
            await i.edit_original_response(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Nome", style=discord.ButtonStyle.gray, row=1)
        async def nome_btn(self, i, b):
            await i.response.send_modal(EasyThreads.InputModal(self.cog, "nome", "Nome da Thread", "{user} = Autor"))

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray, row=1)
        async def msg_btn(self, i, b):
            await i.response.send_modal(EasyThreads.InputModal(self.cog, "mensagem", "Mensagem Inicial", "Texto da thread"))

        @discord.ui.button(label="Privada", style=discord.ButtonStyle.gray, row=2)
        async def priv_btn(self, i, b):
            await i.response.defer()
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            await set_cfg(self.cog.bot, i.guild.id, {"private": not cfg.get("private", False)})
            await i.edit_original_response(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Fixar Msg", style=discord.ButtonStyle.gray, row=2)
        async def pin_btn(self, i, b):
            await i.response.defer()
            cfg = await get_cfg(self.cog.bot, i.guild.id)
            await set_cfg(self.cog.bot, i.guild.id, {"pin": not cfg.get("pin", False)})
            await i.edit_original_response(embed=await self.cog.build_embed(i.guild))

    # --- MODAL À PROVA DE TIMEOUT ---
    class InputModal(discord.ui.Modal):
        def __init__(self, cog, field, title, hint):
            super().__init__(title=title)
            self.cog, self.field = cog, field
            self.text_input = discord.ui.TextInput(label=hint, style=discord.TextStyle.paragraph, required=True)
            self.add_item(self.text_input)

        async def on_submit(self, interaction):
            # Primeiro defer para o Discord não cancelar
            await interaction.response.defer(ephemeral=True)
            # Depois salva
            await set_cfg(self.cog.bot, interaction.guild.id, {self.field: self.text_input.value})
            # Por fim, tenta atualizar a mensagem do painel
            try:
                await interaction.message.edit(embed=await self.cog.build_embed(interaction.guild))
                await interaction.followup.send(f"✅ `{self.field}` atualizado!", ephemeral=True)
            except Exception:
                await interaction.followup.send("✅ Configuração salva!", ephemeral=True)

    @app_commands.command(name="autothread", description="Painel Easy Threads v2")
    async def autothread_cmd(self, i: discord.Interaction):
        embed = await self.build_embed(i.guild)
        await i.response.send_message(embed=embed, view=self.MainView(self))

    @commands.Cog.listener()
    async def on_message(self, m):
        if not m.guild or m.author.bot: return
        cfg = await get_cfg(self.bot, m.guild.id)
        if not cfg.get("ativo") or str(m.channel.id) != str(cfg.get("channel_id")): return

        try:
            nome = cfg.get("nome", "Thread de {user}").replace("{user}", m.author.name)
            thread = await m.create_thread(name=nome, auto_archive_duration=1440)
            msg = await thread.send(f"{m.author.mention} {cfg.get('mensagem', 'Bem-vindo!')}")
            if cfg.get("pin"): await msg.pin()
        except Exception as e:
            print(f"Erro na thread: {e}")

async def setup(bot):
    await bot.add_cog(EasyThreads(bot))
        
