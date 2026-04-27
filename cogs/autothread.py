import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# 🛡️ FUNÇÕES CORRIGIDAS DO BANCO DE DADOS
# ==========================================
async def get_config(bot, guild_id):
    if getattr(bot, 'db', None) is None: return {}
    try:
        # Acesso correto ao MongoDB usando colchetes []
        col = bot.db["autothreads"] 
        data = await col.find_one({"guild_id": guild_id})
        return data or {}
    except Exception as e:
        print(f"Erro no DB (GET): {e}")
        return {}

async def save_config(bot, guild_id, update_data):
    if getattr(bot, 'db', None) is None: return
    try:
        # Acesso correto ao MongoDB usando colchetes []
        col = bot.db["autothreads"]
        await col.update_one({"guild_id": guild_id}, {"$set": update_data}, upsert=True)
    except Exception as e:
        print(f"Erro no DB (SAVE): {e}")

async def build_embed(bot, guild):
    config = await get_config(bot, guild.id)
    canal_id = config.get("channel_id", 0)
    canal = guild.get_channel(canal_id)
    status = "🟢 Ativado" if config.get("ativo", False) else "🔴 Desativado"

    embed = discord.Embed(title="🧵 Painel Autothread", color=discord.Color.blurple())
    embed.description = f"""
**Status do Sistema:** {status}
**Canal Alvo:** {canal.mention if canal else '`Nenhum canal selecionado`'}

**Nome da Thread:** `{config.get('nome', 'Thread de {user}')}`
**Mensagem Inicial:** `{config.get('mensagem', 'Sua thread foi criada.')[:50]}`
"""
    return embed

# ==========================================
# 🎛️ MODAIS DE CONFIGURAÇÃO
# ==========================================
class ConfigModal(discord.ui.Modal):
    def __init__(self, bot, chave, label, placeholder):
        super().__init__(title=f"Configurar {chave.capitalize()}")
        self.bot = bot
        self.chave = chave
        self.entrada = discord.ui.TextInput(
            label=label,
            style=discord.TextStyle.short if chave == "nome" else discord.TextStyle.paragraph,
            placeholder=placeholder,
            required=True
        )
        self.add_item(self.entrada)

    async def on_submit(self, interaction: discord.Interaction):
        # Agora sim vai salvar corretamente!
        await save_config(self.bot, interaction.guild.id, {self.chave: self.entrada.value})
        
        # Atualiza a mensagem na mesma hora
        embed_atualizado = await build_embed(self.bot, interaction.guild)
        await interaction.response.edit_message(embed=embed_atualizado)
        await interaction.followup.send(f"✅ {self.chave.capitalize()} alterado com sucesso!", ephemeral=True)

# ==========================================
# 🎛️ BOTÕES E MENUS DO PAINEL
# ==========================================
class AutoThreadView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Ligar / Desligar", style=discord.ButtonStyle.secondary, custom_id="btn_toggle")
    async def btn_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await get_config(self.bot, interaction.guild.id)
        novo_status = not config.get("ativo", False)
        
        await save_config(self.bot, interaction.guild.id, {"ativo": novo_status})
        await interaction.response.edit_message(embed=await build_embed(self.bot, interaction.guild))
        
        texto = "ativado" if novo_status else "desativado"
        await interaction.followup.send(f"✅ O sistema foi **{texto}**!", ephemeral=True)

    @discord.ui.button(label="Mudar Nome", style=discord.ButtonStyle.primary, custom_id="btn_nome")
    async def btn_nome(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConfigModal(self.bot, "nome", "Nome da thread", "Ex: Dúvida de {user}"))

    @discord.ui.button(label="Mudar Mensagem", style=discord.ButtonStyle.primary, custom_id="btn_msg")
    async def btn_msg(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConfigModal(self.bot, "mensagem", "Mensagem dentro da thread", "O que o bot deve falar?"))

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Selecione o canal das threads...")
    async def select_canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        canal = select.values[0]
        await save_config(self.bot, interaction.guild.id, {"channel_id": canal.id})
        await interaction.response.edit_message(embed=await build_embed(self.bot, interaction.guild))
        await interaction.followup.send(f"✅ Canal definido para {canal.mention}!", ephemeral=True)


# ==========================================
# ⚙️ COG PRINCIPAL E EVENTOS
# ==========================================
class AutoThreadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="autothread", description="Abre o painel de configuração do AutoThread")
    @app_commands.default_permissions(administrator=True)
    async def autothread_cmd(self, interaction: discord.Interaction):
        embed = await build_embed(self.bot, interaction.guild)
        view = AutoThreadView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or isinstance(message.channel, discord.Thread):
            return

        config = await get_config(self.bot, message.guild.id)
        if not config.get("ativo", False) or message.channel.id != config.get("channel_id"):
            return

        try:
            nome_thread = config.get("nome", "Thread de {user}").replace("{user}", message.author.name)
            thread = await message.create_thread(name=nome_thread, auto_archive_duration=1440)
            msg_texto = config.get("mensagem", "Sua thread foi criada.")
            if msg_texto:
                await thread.send(f"{message.author.mention} {msg_texto}")
        except Exception as e:
            print(f"Erro ao criar thread: {e}")

async def setup(bot):
    await bot.add_cog(AutoThreadCog(bot))
        
