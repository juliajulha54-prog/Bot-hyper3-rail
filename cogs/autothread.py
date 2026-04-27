import discord
from discord.ext import commands
from discord import app_commands
import asyncio

# --- SISTEMA DE DADOS SEGURO ---
async def get_guild_data(bot, guild_id):
    """Recupera os dados do banco com verificação de erro"""
    if not hasattr(bot, 'db') or bot.db is None:
        return {}
    try:
        # Tenta acessar a coleção 'autothreads'
        col = bot.db["autothreads"]
        data = await col.find_one({"guild_id": guild_id})
        return data or {}
    except Exception as e:
        print(f"Erro ao ler banco: {e}")
        return {}

async def update_guild_data(bot, guild_id, update_dict):
    """Atualiza os dados garantindo que a conexão exista"""
    if not hasattr(bot, 'db') or bot.db is None:
        return
    try:
        col = bot.db["autothreads"]
        await col.update_one(
            {"guild_id": guild_id}, 
            {"$set": update_dict}, 
            upsert=True
        )
    except Exception as e:
        print(f"Erro ao salvar banco: {e}")

class AutoThreadEasy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_status_label(self, value):
        return "🟢 `Ativado`" if value else "🔴 `Desativado`"

    # --- VISUAL DO EMBED (IGUAL AO VÍDEO) ---
    async def build_embed(self, guild):
        cfg = await get_guild_data(self.bot, guild.id)
        canal = guild.get_channel(cfg.get("channel_id", 0))
        
        embed = discord.Embed(title="🧵 Configuração Autothread", color=0x2b2d31)
        
        embed.add_field(
            name="📍 Canal Alvo", 
            value=canal.mention if canal else "❌ `Não definido`", 
            inline=True
        )
        embed.add_field(
            name="Status", 
            value=self.get_status_label(cfg.get("ativo")), 
            inline=True
        )
        
        config_info = (
            f"**Nome:** `{cfg.get('nome', 'Thread de {user}')}`\n"
            f"**Mensagem:** `{cfg.get('mensagem', 'Sua thread foi criada.')[:40]}...`\n"
            f"**Delay:** `{cfg.get('delay', 0)}s` | **Cooldown:** `{cfg.get('cooldown', 0)}s`"
        )
        embed.add_field(name="📝 Definições de Texto", value=config_info, inline=False)

        opcoes = (
            f"Ignorar Bots: {self.get_status_label(cfg.get('ignorebots'))}\n"
            f"Fixar Mensagem: {self.get_status_label(cfg.get('pin'))}\n"
            f"Thread Privada: {self.get_status_label(cfg.get('private'))}\n"
            f"Bloquear Convites: {self.get_status_label(cfg.get('block_invites'))}"
        )
        embed.add_field(name="⚙️ Opções Adicionais", value=opcoes, inline=False)
        
        embed.set_footer(text="Easy Threads Clone • Use os botões para configurar")
        return embed

    # --- PAINEL DE CONTROLE (BOTÕES EM PORTUGUÊS) ---
    class EasyView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        # FILEIRA 0: OBRIGATÓRIOS
        @discord.ui.button(label="Canal", style=discord.ButtonStyle.gray, row=0)
        async def canal_btn(self, interaction, button):
            # Seletor de canal como visto no vídeo
            select_view = discord.ui.View()
            select = discord.ui.ChannelSelect(
                placeholder="Selecione o canal das threads...", 
                channel_types=[discord.ChannelType.text]
            )
            
            async def select_callback(it):
                await update_guild_data(self.cog.bot, it.guild.id, {"channel_id": select.values[0].id})
                await it.response.send_message(f"✅ Canal {select.values[0].mention} configurado!", ephemeral=True)
                # Atualiza o painel principal
                await interaction.edit_original_response(embed=await self.cog.build_embed(it.guild))
            
            select.callback = select_callback
            select_view.add_item(select)
            await interaction.response.send_message("Escolha o canal alvo:", view=select_view, ephemeral=True)

        @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.blurple, row=0)
        async def toggle_main(self, interaction, button):
            cfg = await get_guild_data(self.cog.bot, interaction.guild.id)
            
            # Bloqueio obrigatório visto no vídeo
            if not cfg.get("channel_id"):
                return await interaction.response.send_message(
                    "❌ **Erro:** Você precisa definir um **Canal** antes de ativar!", 
                    ephemeral=True
                )
            
            await update_guild_data(self.cog.bot, interaction.guild.id, {"ativo": not cfg.get("ativo", False)})
            await interaction.response.edit_message(embed=await self.cog.build_embed(interaction.guild))

        # FILEIRA 1: ENTRADA DE TEXTO
        @discord.ui.button(label="Nome", style=discord.ButtonStyle.gray, row=1)
        async def nome_btn(self, i, b):
            await i.response.send_modal(AutoThreadEasy.InputModal(self.cog, "nome", "Nome da Thread", "{user} = Nome do Autor"))

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray, row=1)
        async def msg_btn(self, i, b):
            await i.response.send_modal(AutoThreadEasy.InputModal(self.cog, "mensagem", "Mensagem Inicial", "Texto enviado na thread"))

        # FILEIRA 2: SWITCHES RÁPIDOS
        @discord.ui.button(label="Ignorar Bots", style=discord.ButtonStyle.gray, row=2)
        async def bots_toggle(self, i, b):
            cfg = await get_guild_data(self.cog.bot, i.guild.id)
            await update_guild_data(self.cog.bot, i.guild.id, {"ignorebots": not cfg.get("ignorebots", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Fixar Msg", style=discord.ButtonStyle.gray, row=2)
        async def pin_toggle(self, i, b):
            cfg = await get_guild_data(self.cog.bot, i.guild.id)
            await update_guild_data(self.cog.bot, i.guild.id, {"pin": not cfg.get("pin", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Privada", style=discord.ButtonStyle.gray, row=2)
        async def private_toggle(self, i, b):
            cfg = await get_guild_data(self.cog.bot, i.guild.id)
            await update_guild_data(self.cog.bot, i.guild.id, {"private": not cfg.get("private", False)})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

    # --- MODAL PARA TEXTOS ---
    class InputModal(discord.ui.Modal):
        def __init__(self, cog, field, title, placeholder):
            super().__init__(title=title)
            self.cog = cog
            self.field = field
            self.value_input = discord.ui.TextInput(
                label=placeholder, 
                style=discord.TextStyle.paragraph, 
                required=True
            )
            self.add_item(self.value_input)

        async def on_submit(self, interaction):
            await update_guild_data(self.cog.bot, interaction.guild.id, {self.field: self.value_input.value})
            await interaction.response.send_message(f"✅ Campo `{self.field}` atualizado!", ephemeral=True)
            # Atualiza a mensagem original que contém o painel
            await interaction.message.edit(embed=await self.cog.build_embed(interaction.guild))

    # --- COMANDO PRINCIPAL ---
    @app_commands.command(name="autothread", description="Abre o painel de configuração estilo Easy Threads")
    async def autothread_cmd(self, interaction: discord.Interaction):
        embed = await self.build_embed(interaction.guild)
        view = self.EasyView(self)
        await interaction.response.send_message(embed=embed, view=view)

    # --- LÓGICA DE CRIAÇÃO AUTOMÁTICA ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot:
            return

        cfg = await get_guild_data(self.bot, message.guild.id)
        
        # Verificações de ativação
        if not cfg.get("ativo") or message.channel.id != cfg.get("channel_id"):
            return
        
        if cfg.get("ignorebots") and message.author.bot:
            return

        try:
            # Formata o nome substituindo {user}
            nome_raw = cfg.get("nome", "Thread de {user}")
            nome_final = nome_raw.replace("{user}", message.author.name)
            
            # Cria a thread (Pública ou Privada)
            thread = await message.create_thread(
                name=nome_final, 
                auto_archive_duration=1440
            )
            
            # Envia a mensagem inicial
            msg_content = cfg.get("mensagem", "Sua thread foi criada.")
            sent_msg = await thread.send(f"{message.author.mention} {msg_content}")
            
            # Fixa se solicitado
            if cfg.get("pin"):
                await sent_msg.pin()
                
        except Exception as e:
            print(f"Erro ao processar autothread: {e}")

async def setup(bot):
    await bot.add_cog(AutoThreadEasy(bot))
                          
