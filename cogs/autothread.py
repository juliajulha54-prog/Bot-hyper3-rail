import discord
from discord.ext import commands
from discord import app_commands
import uuid

# ----------------- BANCO (Lógica de Múltiplos Docs) -----------------

async def set_cfg(bot, config_id, update_dict):
    col = bot.db["autothreads"]
    col.update_one({"config_id": config_id}, {"$set": update_dict}, upsert=True)

async def get_cfg(bot, config_id):
    return bot.db["autothreads"].find_one({"config_id": config_id})

# ----------------- COG PRINCIPAL -----------------

class EasyThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- COMANDOS ---

    @app_commands.command(name="autothread", description="Criar nova configuração")
    async def autothread(self, interaction: discord.Interaction):
        config_id = str(uuid.uuid4())[:8]
        await set_cfg(self.bot, config_id, {
            "guild_id": str(interaction.guild.id),
            "ativo": False, "channel_id": None, "nome": "Thread de {user}",
            "mensagem": "Sua thread foi criada.", "cooldown": 0,
            "ignore_bots": True, "pin": False, "lock": False
        })
        await interaction.response.send_message(f"✅ Painel criado (ID: `{config_id}`)", 
                                                view=self.MainView(self, config_id), ephemeral=True)

    @app_commands.command(name="list", description="Listar configurações")
    async def list_configs(self, interaction: discord.Interaction):
        configs = list(self.bot.db["autothreads"].find({"guild_id": str(interaction.guild.id)}))
        if not configs: return await interaction.response.send_message("Nenhuma config.", ephemeral=True)
        
        embed = discord.Embed(title="🧵 Configurações Ativas", color=0x2b2d31)
        for c in configs:
            embed.add_field(name=f"ID: {c['config_id']}", value=f"Canal: <#{c.get('channel_id')}> | Ativo: {c.get('ativo')}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ----------------- VIEW E BOTÕES -----------------

    class MainView(discord.ui.View):
        def __init__(self, cog, config_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.config_id = config_id

        async def _toggle(self, interaction, field):
            cfg = await get_cfg(self.cog.bot, self.config_id)
            val = not cfg.get(field, False)
            await set_cfg(self.cog.bot, self.config_id, {field: val})
            await interaction.response.send_message(f"✅ {field} definido como {val}", ephemeral=True, delete_after=2)

        @discord.ui.button(label="Canal", style=discord.ButtonStyle.gray, row=0)
        async def canal(self, i, b):
            select = discord.ui.ChannelSelect(callback=lambda sel: self.cog.bot.loop.create_task(self.set_chan(i, sel)))
            view = discord.ui.View().add_item(select)
            await i.response.send_message("Escolha o canal:", view=view, ephemeral=True)

        async def set_chan(self, i, sel):
            await set_cfg(self.cog.bot, self.config_id, {"channel_id": str(sel.values[0].id)})
            await i.edit_original_response(content="✅ Canal definido!", view=None)

        @discord.ui.button(label="Ativar", style=discord.ButtonStyle.green, row=0)
        async def toggle(self, i, b): await self._toggle(i, "ativo")

        @discord.ui.button(label="Ignore Bots", style=discord.ButtonStyle.blurple, row=0)
        async def bot_ign(self, i, b): await self._toggle(i, "ignore_bots")

        @discord.ui.button(label="Pin Thread", style=discord.ButtonStyle.blurple, row=1)
        async def pin(self, i, b): await self._toggle(i, "pin")

        @discord.ui.button(label="Lock Thread", style=discord.ButtonStyle.blurple, row=1)
        async def lock(self, i, b): await self._toggle(i, "lock")
        
        @discord.ui.button(label="Nome", style=discord.ButtonStyle.gray, row=2)
        async def nome(self, i, b): await i.response.send_modal(EasyThreads.Modal(self.cog, self.config_id, "nome"))

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.gray, row=2)
        async def msg(self, i, b): await i.response.send_modal(EasyThreads.Modal(self.cog, self.config_id, "mensagem"))

    # ----------------- MODAL E EVENTO -----------------

    class Modal(discord.ui.Modal):
        def __init__(self, cog, cid, field):
            super().__init__(title="Editar")
            self.cog, self.cid, self.field = cog, cid, field
            self.add_item(discord.ui.TextInput(label="Novo valor", custom_id="val"))
        async def on_submit(self, i):
            await set_cfg(self.cog.bot, self.cid, {self.field: i.data['components'][0]['components'][0]['value']})
            await i.response.send_message("✅ Atualizado!", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        # Busca todas as configs do servidor
        configs = self.bot.db["autothreads"].find({"guild_id": str(message.guild.id), "ativo": True})
        for cfg in configs:
            if str(message.channel.id) == str(cfg.get("channel_id")):
                if cfg.get("ignore_bots") and message.author.bot: continue
                
                thread = await message.create_thread(name=cfg.get("nome", "Thread").replace("{user}", message.author.name))
                msg = await thread.send(f"{message.author.mention} {cfg.get('mensagem')}")
                if cfg.get("pin"): await msg.pin()
                if cfg.get("lock"): await thread.edit(locked=True)

async def setup(bot):
    await bot.add_cog(EasyThreads(bot))
        
