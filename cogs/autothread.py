import discord
from discord.ext import commands
from discord import app_commands

# --- CORREÇÃO: Função de persistência ---
async def update_panel(interaction, bot, guild):
    # Esta função força a atualização da mensagem do painel
    embed = await build_embed(bot, guild)
    # Tenta editar a mensagem atual da interação
    try:
        await interaction.response.edit_message(embed=embed)
    except:
        # Se a interação expirou, edita a mensagem original
        await interaction.message.edit(embed=embed)

async def get_config(bot, guild_id):
    if getattr(bot, 'db', None) is None: return {}
    col = bot.db["autothreads"]
    data = await col.find_one({"guild_id": guild_id})
    return data or {}

async def save_config(bot, guild_id, update_data):
    if getattr(bot, 'db', None) is None: return
    col = bot.db["autothreads"]
    await col.update_one({"guild_id": guild_id}, {"$set": update_data}, upsert=True)

async def build_embed(bot, guild):
    config = await get_config(bot, guild.id)
    canal = guild.get_channel(config.get("channel_id", 0))
    status = "🟢 Ativado" if config.get("ativo", False) else "🔴 Desativado"
    return discord.Embed(title="🧵 Painel Autothread", description=f"Status: {status}\nCanal: {canal.mention if canal else 'Nenhum'}\nNome: `{config.get('nome', 'Thread de {user}')}`\nMensagem: `{config.get('mensagem', 'Sua thread foi criada.')[:50]}`", color=discord.Color.blurple())

class ConfigModal(discord.ui.Modal):
    def __init__(self, bot, chave, label):
        super().__init__(title="Configurar")
        self.bot = bot
        self.chave = chave
        self.input = discord.ui.TextInput(label=label, style=discord.TextStyle.paragraph)
        self.add_item(self.input)
    async def on_submit(self, i):
        await save_config(self.bot, i.guild.id, {self.chave: self.input.value})
        await i.response.send_message("✅ Atualizado!", ephemeral=True)
        # Força a edição da mensagem pai
        await i.message.edit(embed=await build_embed(self.bot, i.guild))

class AutoThreadView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Ligar/Desligar", style=discord.ButtonStyle.secondary, custom_id="persist_toggle")
    async def toggle(self, i, b):
        cfg = await get_config(self.bot, i.guild.id)
        await save_config(self.bot, i.guild.id, {"ativo": not cfg.get("ativo", False)})
        await i.response.edit_message(embed=await build_embed(self.bot, i.guild))

    @discord.ui.button(label="Nome", style=discord.ButtonStyle.primary, custom_id="persist_nome")
    async def nome(self, i, b): await i.response.send_modal(ConfigModal(self.bot, "nome", "Novo nome"))

    @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.primary, custom_id="persist_msg")
    async def msg(self, i, b): await i.response.send_modal(ConfigModal(self.bot, "mensagem", "Nova mensagem"))

class AutoThreadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="autothread")
    async def autothread(self, i: discord.Interaction):
        view = AutoThreadView(self.bot)
        view.add_item(discord.ui.ChannelSelect(placeholder="Mudar canal...", callback=self.select_canal))
        await i.response.send_message(embed=await build_embed(self.bot, i.guild), view=view)

    async def select_canal(self, i: discord.Interaction):
        await save_config(self.bot, i.guild.id, {"channel_id": int(i.data['values'][0])})
        await i.response.edit_message(embed=await build_embed(self.bot, i.guild))

async def setup(bot):
    await bot.add_cog(AutoThreadCog(bot))
    
