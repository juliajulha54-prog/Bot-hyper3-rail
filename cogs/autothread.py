import discord
from discord.ext import commands
from discord import app_commands
import uuid
import re

# ---------------- BANCO ----------------

async def get_all_cfg(bot, guild_id):
    return list(bot.db["autothreads"].find({"guild_id": str(guild_id)}))

async def get_cfg(bot, config_id):
    return bot.db["autothreads"].find_one({"config_id": config_id})

async def set_cfg(bot, config_id, data):
    bot.db["autothreads"].update_one(
        {"config_id": config_id},
        {"$set": data},
        upsert=True
    )

async def delete_cfg(bot, config_id):
    bot.db["autothreads"].delete_one({"config_id": config_id})


# ---------------- COG ----------------

class EasyThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def status(self, v):
        return "🟢 Ativado" if v else "🔴 Desativado"

    # ---------------- EMBED ----------------

    async def build_embed(self, guild, cfg):
        canal = guild.get_channel(int(cfg.get("channel_id"))) if cfg.get("channel_id") else None

        embed = discord.Embed(title="🧵 Easy Threads", color=0x2b2d31)

        embed.add_field(
            name="📍 Canal",
            value=canal.mention if canal else "❌ Não definido",
            inline=True
        )

        embed.add_field(
            name="Status",
            value=self.status(cfg.get("ativo")),
            inline=True
        )

        embed.add_field(
            name="📝 Configurações",
            value=(
                f"Nome: `{cfg.get('nome', 'Thread de {user}')}`\n"
                f"Mensagem: `{cfg.get('mensagem', 'Bem-vindo!')[:40]}`"
            ),
            inline=False
        )

        embed.add_field(
            name="⚙️ Opções",
            value=(
                f"Ignorar Bots: {self.status(cfg.get('ignorebots'))}\n"
                f"Fixar: {self.status(cfg.get('pin'))}\n"
                f"Privada: {self.status(cfg.get('private'))}\n"
                f"Bloquear Convites: {self.status(cfg.get('block_invites'))}"
            ),
            inline=False
        )

        return embed

    # ---------------- VIEW CONFIG ----------------

    class ConfigView(discord.ui.View):
        def __init__(self, cog, config_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.config_id = config_id

        async def update(self, interaction):
            cfg = await get_cfg(self.cog.bot, self.config_id)
            await interaction.message.edit(
                embed=await self.cog.build_embed(interaction.guild, cfg),
                view=self
            )

        @discord.ui.button(label="Excluir", style=discord.ButtonStyle.red)
        async def delete(self, i: discord.Interaction, b):
            await delete_cfg(self.cog.bot, self.config_id)
            await i.response.edit_message(content="❌ Configuração excluída.", embed=None, view=None)

    # ---------------- VIEW LIST ----------------

    class ListView(discord.ui.View):
        def __init__(self, cog, data):
            super().__init__(timeout=120)
            self.cog = cog
            self.data = data

            options = [
                discord.SelectOption(
                    label=f"Config {i+1}",
                    description=f"Canal: {cfg.get('channel_id')}",
                    value=cfg["config_id"]
                )
                for i, cfg in enumerate(data)
            ]

            self.select = discord.ui.Select(placeholder="Escolha uma config", options=options)
            self.select.callback = self.select_callback
            self.add_item(self.select)

        async def select_callback(self, interaction: discord.Interaction):
            config_id = self.select.values[0]
            cfg = await get_cfg(self.cog.bot, config_id)

            embed = await self.cog.build_embed(interaction.guild, cfg)

            view = EasyThreads.ConfigView(self.cog, config_id)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ---------------- COMANDOS ----------------

    @app_commands.command(name="autothread", description="Criar novo painel")
    async def autothread(self, interaction: discord.Interaction):

        config_id = str(uuid.uuid4())

        await set_cfg(self.bot, config_id, {
            "guild_id": str(interaction.guild.id),
            "config_id": config_id,
            "ativo": False
        })

        cfg = await get_cfg(self.bot, config_id)

        await interaction.response.send_message(
            embed=await self.build_embed(interaction.guild, cfg)
        )

        msg = await interaction.original_response()
        await msg.edit(view=self.ConfigView(self, config_id))

    # 🔥 LISTA COMPLETA
    @app_commands.command(name="autothread_list", description="Listar configs ativas")
    async def listar(self, interaction: discord.Interaction):

        data = await get_all_cfg(self.bot, interaction.guild.id)

        ativos = [cfg for cfg in data if cfg.get("ativo")]

        if not ativos:
            return await interaction.response.send_message("❌ Nenhuma config ativa.")

        desc = ""
        for i, cfg in enumerate(ativos, 1):
            canal = interaction.guild.get_channel(int(cfg.get("channel_id"))) if cfg.get("channel_id") else None

            desc += (
                f"**{i}.** {canal.mention if canal else 'Sem canal'}\n"
                f"Nome: `{cfg.get('nome','Thread')}`\n"
                f"Mensagem: `{cfg.get('mensagem','...')[:30]}`\n"
                f"{self.status(cfg.get('ativo'))}\n\n"
            )

        embed = discord.Embed(
            title="📋 Configurações Ativas",
            description=desc,
            color=0x2b2d31
        )

        await interaction.response.send_message(
            embed=embed,
            view=self.ListView(self, ativos)
        )

    # ---------------- EVENTO ----------------

    @commands.Cog.listener()
    async def on_message(self, m):
        if not m.guild:
            return

        data = await get_all_cfg(self.bot, m.guild.id)

        for cfg in data:
            if not cfg.get("ativo"):
                continue

            if str(m.channel.id) != str(cfg.get("channel_id")):
                continue

            # 🔒 bloqueador de convite
            if cfg.get("block_invites"):
                if re.search(r"(discord\.gg|discord\.com/invite)", m.content):
                    await m.delete()
                    return

            if cfg.get("ignorebots") and m.author.bot:
                continue

            try:
                nome = cfg.get("nome", "Thread de {user}").replace("{user}", m.author.name)

                thread = await m.create_thread(name=nome)

                msg = await thread.send(
                    f"{m.author.mention} {cfg.get('mensagem', 'Bem-vindo!')}"
                )

                if cfg.get("pin"):
                    await msg.pin()

            except Exception as e:
                print("Erro:", e)


async def setup(bot):
    await bot.add_cog(EasyThreads(bot))
