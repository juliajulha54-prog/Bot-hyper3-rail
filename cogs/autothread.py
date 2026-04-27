import discord
from discord.ext import commands
from discord import app_commands

class AutoThread(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}

    def get_col(self):
        return self.bot.db.get("autothreads") if hasattr(self.bot, 'db') else None

    async def get_config(self, gid):
        if gid in self.cache: return self.cache[gid]
        col = self.get_col()
        if col is None: return {}
        data = await col.find_one({"guild_id": gid}) or {}
        self.cache[gid] = data
        return data

    async def update_config(self, gid, data):
        col = self.get_col()
        if col:
            await col.update_one({"guild_id": gid}, {"$set": data}, upsert=True)
            self.cache[gid] = await col.find_one({"guild_id": gid})

    async def build_embed(self, guild):
        cfg = await self.get_config(guild.id)
        canal = guild.get_channel(cfg.get("channel_id", 0))
        return discord.Embed(
            title="🧵 Painel Autothread",
            description=f"Status: {'🟢 Ativo' if cfg.get('ativo') else '🔴 Desativado'}\nCanal: {canal.mention if canal else 'Não definido'}\nNome: `{cfg.get('nome', 'Thread de {user}')}`\nMensagem: `{cfg.get('mensagem', 'Padrão')[:50]}`",
            color=discord.Color.blurple()
        )

    # --- View com botões funcionais ---
    class PanelView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="Ativar/Desativar", style=discord.ButtonStyle.secondary)
        async def toggle(self, i, b):
            cfg = await self.cog.get_config(i.guild.id)
            new_state = not cfg.get("ativo", False)
            await self.cog.update_config(i.guild.id, {"ativo": new_state})
            await i.response.edit_message(embed=await self.cog.build_embed(i.guild))

        @discord.ui.button(label="Nome", style=discord.ButtonStyle.blurple)
        async def nome(self, i, b):
            await i.response.send_modal(AutoThread.ModalConfig(self.cog, "nome", "Novo nome da thread"))

        @discord.ui.button(label="Mensagem", style=discord.ButtonStyle.blurple)
        async def msg(self, i, b):
            await i.response.send_modal(AutoThread.ModalConfig(self.cog, "mensagem", "Nova mensagem"))

    class ModalConfig(discord.ui.Modal):
        def __init__(self, cog, key, label):
            super().__init__(title="Configurar")
            self.cog = cog
            self.key = key
            self.input = discord.ui.TextInput(label=label, style=discord.TextStyle.paragraph)
            self.add_item(self.input)

        async def on_submit(self, i):
            await self.cog.update_config(i.guild.id, {self.key: self.input.value})
            await i.response.send_message(f"✅ {self.key.capitalize()} alterado com sucesso!", ephemeral=True)
            # Atualiza o painel original
            await i.message.edit(embed=await self.cog.build_embed(i.guild))

    @app_commands.command(name="autothread")
    async def autothread(self, i: discord.Interaction):
        view = self.PanelView(self)
        # Adiciona o seletor de canal dinamicamente
        view.add_item(discord.ui.ChannelSelect(placeholder="Mudar canal...", callback=self.select_canal))
        await i.response.send_message(embed=await self.build_embed(i.guild), view=view)

    async def select_canal(self, i: discord.Interaction):
        await self.update_config(i.guild.id, {"channel_id": i.data['values'][0]})
        await i.response.send_message("✅ Canal alterado!", ephemeral=True)
        await i.message.edit(embed=await self.build_embed(i.guild))

async def setup(bot):
    await bot.add_cog(AutoThread(bot))
        
