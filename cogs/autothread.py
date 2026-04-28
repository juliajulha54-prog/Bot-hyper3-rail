import discord
from discord.ext import commands
from discord import app_commands
import uuid
import re

invite_regex = re.compile(r"(discord\.gg/|discord\.com/invite/)")
emoji_regex = re.compile(r"<a?:\w+:\d+>")  # 🔥 remove emoji custom se der erro

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

    async def build_embed(self, guild, cfg):
        canal = guild.get_channel(int(cfg.get("channel_id"))) if cfg.get("channel_id") else None

        embed = discord.Embed(title="🧵 Criação de novo canal AutoThreads", color=0x2b2d31)

        embed.add_field(name="📍 Canal", value=canal.mention if canal else "❌ Não definido", inline=True)
        embed.add_field(name="Status", value=self.status(cfg.get("ativo")), inline=True)

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

    # ---------------- VIEW ----------------

    class View(discord.ui.View):
        def __init__(self, cog, config_id, owner_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.config_id = config_id
            self.owner_id = owner_id

        async def interaction_check(self, interaction: discord.Interaction):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Comando restrito.", ephemeral=True)
                return False

            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("❌ Apenas quem solicitou o painel pode usar.", ephemeral=True)
                return False

            return True

        async def update(self, interaction):
            cfg = await get_cfg(self.cog.bot, self.config_id)
            await interaction.message.edit(
                embed=await self.cog.build_embed(interaction.guild, cfg),
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
                    "channel_id": str(channel_id)
                })

                await self.update(i)
                await x.followup.send("✅ Canal setado com sucesso.", ephemeral=True)

            select.callback = cb
            view.add_item(select)

            await i.response.send_message("Escolha o canal:", view=view, ephemeral=True)

        @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.blurple)
        async def toggle(self, i, b):
            cfg = await get_cfg(self.cog.bot, self.config_id)

            if not cfg.get("channel_id") or not cfg.get("nome") or not cfg.get("mensagem"):
                return await i.response.send_message(
                    "❌ Configure Canal, Nome e Mensagem antes de ativar.",
                    ephemeral=True
                )

            await set_cfg(self.cog.bot, self.config_id, {
                "ativo": not cfg.get("ativo", False)
            })

            await self.update(i)
            await i.response.defer()

        @discord.ui.button(label="Nome")
        async def nome(self, i, b):
            await i.response.send_modal(
                EasyThreads.Modal(self.cog, self.config_id, "nome", "Nome da Thread")
            )

        @discord.ui.button(label="Mensagem")
        async def mensagem(self, i, b):
            await i.response.send_modal(
                EasyThreads.Modal(self.cog, self.config_id, "mensagem", "Mensagem inicial")
            )

        @discord.ui.button(label="Ignorar Bots")
        async def ignore(self, i, b):
            cfg = await get_cfg(self.cog.bot, self.config_id)

            await set_cfg(self.cog.bot, self.config_id, {
                "ignorebots": not cfg.get("ignorebots", False)
            })

            await self.update(i)
            await i.response.defer()

        @discord.ui.button(label="Fixar Msg")
        async def pin(self, i, b):
            cfg = await get_cfg(self.cog.bot, self.config_id)

            await set_cfg(self.cog.bot, self.config_id, {
                "pin": not cfg.get("pin", False)
            })

            await self.update(i)
            await i.response.defer()

        @discord.ui.button(label="Privada")
        async def priv(self, i, b):
            cfg = await get_cfg(self.cog.bot, self.config_id)

            await set_cfg(self.cog.bot, self.config_id, {
                "private": not cfg.get("private", False)
            })

            await self.update(i)
            await i.response.defer()

        @discord.ui.button(label="Bloquear Convites")
        async def block_invites(self, i, b):
            cfg = await get_cfg(self.cog.bot, self.config_id)

            await set_cfg(self.cog.bot, self.config_id, {
                "block_invites": not cfg.get("block_invites", False)
            })

            await self.update(i)
            await i.response.defer()

        @discord.ui.button(label="Excluir", style=discord.ButtonStyle.red, row=3)
        async def delete(self, i: discord.Interaction, b):
            await delete_cfg(self.cog.bot, self.config_id)

            await i.response.edit_message(
                content="❌ Configuração excluída.",
                embed=None,
                view=None
            )

    # ---------------- MODAL ----------------

    class Modal(discord.ui.Modal):
        def __init__(self, cog, config_id, field, title):
            super().__init__(title=title)
            self.cog = cog
            self.config_id = config_id
            self.field = field

            self.input = discord.ui.TextInput(
                label="Digite aqui",
                required=True,
                max_length=2000
            )
            self.add_item(self.input)

        async def on_submit(self, interaction: discord.Interaction):
            await set_cfg(self.cog.bot, self.config_id, {
                self.field: self.input.value
            })

            view = EasyThreads.View(
                self.cog,
                self.config_id,
                (await get_cfg(self.cog.bot, self.config_id))["owner_id"]
            )

            await view.update(interaction)

            if self.field == "mensagem":
                await interaction.response.send_message(
                    f"✅ Mensagem atualizada para:\n**{self.input.value}**",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ Nome atualizado para:\n**{self.input.value}**",
                    ephemeral=True
                )

    # ---------------- COMANDOS ----------------

    @app_commands.command(name="autothread", description="Criar novo painel")
    @app_commands.check(lambda i: i.user.guild_permissions.administrator)
    async def autothread(self, interaction: discord.Interaction):

        config_id = str(uuid.uuid4())

        await set_cfg(self.bot, config_id, {
            "guild_id": str(interaction.guild.id),
            "config_id": config_id,
            "ativo": False,
            "owner_id": interaction.user.id
        })

        cfg = await get_cfg(self.bot, config_id)

        await interaction.response.send_message(
            embed=await self.build_embed(interaction.guild, cfg)
        )

        msg = await interaction.original_response()
        await msg.edit(view=self.View(self, config_id, interaction.user.id))

    @app_commands.command(name="autothread_list", description="Listar configs ativas")
    @app_commands.check(lambda i: i.user.guild_permissions.administrator)
    async def listar(self, interaction: discord.Interaction):

        await interaction.response.defer()

        data = await get_all_cfg(self.bot, interaction.guild.id)
        ativos = [cfg for cfg in data if cfg.get("ativo")][:25]

        if not ativos:
            return await interaction.followup.send("❌ Nenhuma configuração ativa.")

        options = [
            discord.SelectOption(
                label=f"{i+1}",
                description=cfg.get("nome", "Thread"),
                value=cfg["config_id"]
            )
            for i, cfg in enumerate(ativos)
        ]

        view = discord.ui.View()
        select = discord.ui.Select(placeholder="Selecione uma config", options=options)

        async def callback(i: discord.Interaction):
            await i.response.defer(ephemeral=True)

            cfg = await get_cfg(self.bot, select.values[0])
            embed = await self.build_embed(i.guild, cfg)

            action_view = discord.ui.View()

            async def editar(btn_i):
                await btn_i.response.send_message(
                    embed=embed,
                    view=self.View(self, cfg["config_id"], cfg["owner_id"]),
                    ephemeral=True
                )

            async def excluir(btn_i):
                await delete_cfg(self.bot, cfg["config_id"])
                await btn_i.response.send_message("🗑️ Excluído.", ephemeral=True)

            b1 = discord.ui.Button(label="Editar", style=discord.ButtonStyle.blurple)
            b2 = discord.ui.Button(label="Excluir", style=discord.ButtonStyle.red)

            b1.callback = editar
            b2.callback = excluir

            action_view.add_item(b1)
            action_view.add_item(b2)

            await i.followup.send(embed=embed, view=action_view, ephemeral=True)

        select.callback = callback
        view.add_item(select)

        await interaction.followup.send("Selecione uma configuração:", view=view)

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

            if cfg.get("block_invites") and invite_regex.search(m.content):
                try:
                    await m.delete()
                except:
                    pass
                return

            try:
                nome = cfg.get("nome", "Thread de {user}").replace("{user}", m.author.name)

                thread = await m.create_thread(name=nome)

                try:
                    msg = await thread.send(cfg.get("mensagem"))
                except Exception as e:
                    print("ERRO AO ENVIAR MENSAGEM:", repr(e))

                    # 🔥 fallback remove emoji custom
                    safe_msg = emoji_regex.sub("", cfg.get("mensagem"))
                    msg = await thread.send(safe_msg)

                if cfg.get("pin"):
                    await msg.pin()

            except Exception as e:
                print("Erro:", e)


async def setup(bot):
    await bot.add_cog(EasyThreads(bot))
