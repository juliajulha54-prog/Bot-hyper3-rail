import discord
from discord.ext import commands
from discord import app_commands
import uuid

# ---------------- BANCO ----------------

async def get_all_cfg(bot, guild_id):
    col = bot.db["autothreads"]
    return list(col.find({"guild_id": str(guild_id)}))


async def get_cfg(bot, config_id):
    col = bot.db["autothreads"]
    return col.find_one({"config_id": config_id})


async def set_cfg(bot, config_id, data):
    col = bot.db["autothreads"]
    col.update_one(
        {"config_id": config_id},
        {"$set": data},
        upsert=True
    )


# ---------------- COG ----------------

class EasyThreads(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def status(self, v):
        return "🟢 Ativado" if v else "🔴 Desativado"

    async def build_embed(self, guild, cfg):
        canal = guild.get_channel(int(cfg.get("channel_id"))) if cfg.get("channel_id") else None

        return discord.Embed(
            title="🧵 Easy Threads",
            color=0x2b2d31
        ).add_field(
            name="Canal",
            value=canal.mention if canal else "Não definido"
        ).add_field(
            name="Status",
            value=self.status(cfg.get("ativo"))
        ).add_field(
            name="Opções",
            value=(
                f"Ignorar Bots: {self.status(cfg.get('ignorebots'))}\n"
                f"Fixar: {self.status(cfg.get('pin'))}\n"
                f"Privada: {self.status(cfg.get('private'))}"
            ),
            inline=False
        )

    # ---------------- VIEW ----------------

    class View(discord.ui.View):
        def __init__(self, cog, config_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.config_id = config_id

        async def update(self, guild, message):
            cfg = await get_cfg(self.cog.bot, self.config_id)
            await message.edit(
                embed=await self.cog.build_embed(guild, cfg),
                view=self
            )

        @discord.ui.button(label="Canal")
        async def canal(self, i: discord.Interaction, b):
            view = discord.ui.View()
            select = discord.ui.ChannelSelect()

            async def cb(x):
                await x.response.defer(ephemeral=True)

                channel_id = list(x.data["resolved"]["channels"].keys())[0]

                await set_cfg(self.cog.bot, self.config_id, {
                    "channel_id": channel_id
                })

                await self.update(x.guild, i.message)

                await x.followup.send("Canal definido", ephemeral=True)

            select.callback = cb
            view.add_item(select)

            await i.response.send_message("Escolha:", view=view, ephemeral=True)

        @discord.ui.button(label="Ativar")
        async def toggle(self, i, b):
            cfg = await get_cfg(self.cog.bot, self.config_id)

            await set_cfg(self.cog.bot, self.config_id, {
                "ativo": not cfg.get("ativo", False)
            })

            await self.update(i.guild, i.message)
            await i.response.defer()

        @discord.ui.button(label="Ignorar Bots")
        async def ignore(self, i, b):
            cfg = await get_cfg(self.cog.bot, self.config_id)

            await set_cfg(self.cog.bot, self.config_id, {
                "ignorebots": not cfg.get("ignorebots", False)
            })

            await self.update(i.guild, i.message)
            await i.response.defer()

        @discord.ui.button(label="Fixar")
        async def pin(self, i, b):
            cfg = await get_cfg(self.cog.bot, self.config_id)

            await set_cfg(self.cog.bot, self.config_id, {
                "pin": not cfg.get("pin", False)
            })

            await self.update(i.guild, i.message)
            await i.response.defer()

        @discord.ui.button(label="Privada")
        async def priv(self, i, b):
            cfg = await get_cfg(self.cog.bot, self.config_id)

            await set_cfg(self.cog.bot, self.config_id, {
                "private": not cfg.get("private", False)
            })

            await self.update(i.guild, i.message)
            await i.response.defer()

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

        msg = await interaction.response.send_message(
            embed=await self.build_embed(interaction.guild, cfg)
        )

        message = await interaction.original_response()

        await message.edit(view=self.View(self, config_id))

    @app_commands.command(name="autothread_list", description="Listar configs")
    async def listar(self, interaction: discord.Interaction):

        data = await get_all_cfg(self.bot, interaction.guild.id)

        if not data:
            return await interaction.response.send_message("Nenhuma configuração.")

        desc = ""
        for i, cfg in enumerate(data, 1):
            desc += f"{i}. Canal: `{cfg.get('channel_id')}` | {self.status(cfg.get('ativo'))}\n"

        embed = discord.Embed(
            title="Configs Easy Threads",
            description=desc,
            color=0x2b2d31
        )

        await interaction.response.send_message(embed=embed)


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

            if cfg.get("ignorebots") and m.author.bot:
                continue

            try:
                thread = await m.create_thread(
                    name=f"Thread de {m.author.name}"
                )

                msg = await thread.send(m.author.mention)

                if cfg.get("pin"):
                    await msg.pin()

            except Exception as e:
                print("Erro:", e)


async def setup(bot):
    await bot.add_cog(EasyThreads(bot))
