import discord
from discord.ext import commands
import uuid
import re

invite_regex = re.compile(r"(discord.gg/|discord.com/invite/)")
emoji_regex = re.compile(r"<a?:\w+:\d+>")

# ---------------- LINKS AUTORIZADOS ----------------

links_autorizados = [
    "mega.nz",
    "drive.google.com",
    "tiktok.com",
    "streamable.com",
    "cdn.nsb.gg"
]

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

    # 🔗 LINK CHECK
    def link_permitido(self, conteudo: str) -> bool:
        conteudo = conteudo.lower()

        if "discord.gg" in conteudo or "discord.com/invite" in conteudo:
            return False

        if "http://" in conteudo or "https://" in conteudo:
            return any(link in conteudo for link in links_autorizados)

        return True

    async def build_embed(self, guild, cfg):
        canal = guild.get_channel(int(cfg.get("channel_id"))) if cfg.get("channel_id") else None

        embed = discord.Embed(
            title="🧵 Criação de novo canal AutoThreads",
            color=0x2b2d31
        )

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

    # ---------------- VIEW ----------------

    class View(discord.ui.View):
        def __init__(self, cog, config_id, owner_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.config_id = config_id
            self.owner_id = owner_id

        async def interaction_check(self, interaction: discord.Interaction):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
                return False

            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("❌ Só o criador pode usar.", ephemeral=True)
                return False

            return True

        async def update(self, interaction):
            cfg = await get_cfg(self.cog.bot, self.config_id)
            await interaction.message.edit(
                embed=await self.cog.build_embed(interaction.guild, cfg),
                view=self
            )

        # ---------------- BOTÕES ----------------

        @discord.ui.button(label="Canal")
        async def canal(self, i, b):
            view = discord.ui.View()
            select = discord.ui.ChannelSelect()

            async def cb(x):
                await x.response.defer(ephemeral=True)
                channel_id = list(x.data["resolved"]["channels"].keys())[0]

                await set_cfg(self.cog.bot, self.config_id, {
                    "channel_id": str(channel_id)
                })

                await self.update(i)
                await x.followup.send("✅ Canal setado.", ephemeral=True)

            select.callback = cb
            view.add_item(select)

            await i.response.send_message("Escolha o canal:", view=view, ephemeral=True)

        @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.blurple)
        async def toggle(self, i, b):
            cfg = await get_cfg(self.cog.bot, self.config_id)

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
            await i.response.send_message(
                "📩 Envie a nova mensagem (60s)",
                ephemeral=True
            )

            def check(m):
                return m.author.id == i.user.id and m.channel.id == i.channel.id

            try:
                msg = await self.cog.bot.wait_for("message", timeout=60, check=check)

                await set_cfg(self.cog.bot, self.config_id, {
                    "mensagem": msg.content
                })

                try:
                    await msg.delete()
                except:
                    pass

                await self.update(i)

                await i.followup.send("✅ Mensagem atualizada.", ephemeral=True)

            except:
                await i.followup.send("❌ Tempo esgotado.", ephemeral=True)

        # 🔗 BOTÃO LINKS
        @discord.ui.button(label="Links Permitidos", style=discord.ButtonStyle.gray)
        async def links(self, i, b):

            cleaner = self.cog.bot.get_cog("Cleaner")

            if not cleaner:
                return await i.response.send_message("❌ Cleaner não encontrado.", ephemeral=True)

            cfg = await get_cfg(self.cog.bot, self.config_id)
            canal_id = int(cfg.get("channel_id"))

            if canal_id in cleaner.canais_permitidos:
                cleaner.canais_permitidos.remove(canal_id)
                status = "❌ Links bloqueados"
            else:
                cleaner.canais_permitidos.append(canal_id)
                status = "🟢 Links liberados"

            await i.response.send_message(status, ephemeral=True)
            await self.update(i)

        @discord.ui.button(label="Excluir", style=discord.ButtonStyle.red)
        async def delete(self, i, b):
            await delete_cfg(self.cog.bot, self.config_id)

            await i.response.edit_message(
                content="❌ Configuração deletada.",
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

            self.input = discord.ui.TextInput(label="Digite aqui", required=True)
            self.add_item(self.input)

        async def on_submit(self, interaction):
            await set_cfg(self.cog.bot, self.config_id, {
                self.field: self.input.value
            })

            view = EasyThreads.View(
                self.cog,
                self.config_id,
                (await get_cfg(self.cog.bot, self.config_id))["owner_id"]
            )

            await view.update(interaction)

    # ---------------- COMANDOS PREFIXO ----------------

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def autothread(self, ctx):

        config_id = str(uuid.uuid4())

        await set_cfg(self.bot, config_id, {
            "guild_id": str(ctx.guild.id),
            "config_id": config_id,
            "ativo": False,
            "owner_id": ctx.author.id
        })

        cfg = await get_cfg(self.bot, config_id)

        msg = await ctx.send(embed=await self.build_embed(ctx.guild, cfg))
        await msg.edit(view=self.View(self, config_id, ctx.author.id))

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def autothread_list(self, ctx):

        data = await get_all_cfg(self.bot, ctx.guild.id)
        ativos = [cfg for cfg in data if cfg.get("ativo")][:25]

        if not ativos:
            return await ctx.send("❌ Nenhuma config ativa.")

        options = [
            discord.SelectOption(
                label=f"{i+1}",
                description=cfg.get("nome", "Thread"),
                value=cfg["config_id"]
            )
            for i, cfg in enumerate(ativos)
        ]

        view = discord.ui.View()
        select = discord.ui.Select(placeholder="Selecione", options=options)

        async def callback(interaction):
            cfg = await get_cfg(self.bot, select.values[0])

            embed = await self.build_embed(ctx.guild, cfg)

            action_view = discord.ui.View()

            async def editar(i):
                await i.response.send_message(
                    embed=embed,
                    view=self.View(self, cfg["config_id"], cfg["owner_id"]),
                    ephemeral=True
                )

            async def excluir(i):
                await delete_cfg(self.bot, cfg["config_id"])
                await i.response.send_message("🗑️ Excluído.", ephemeral=True)

            b1 = discord.ui.Button(label="Editar", style=discord.ButtonStyle.blurple)
            b2 = discord.ui.Button(label="Excluir", style=discord.ButtonStyle.red)

            b1.callback = editar
            b2.callback = excluir

            action_view.add_item(b1)
            action_view.add_item(b2)

            await interaction.response.send_message(embed=embed, view=action_view, ephemeral=True)

        select.callback = callback
        view.add_item(select)

        await ctx.send("Selecione:", view=view)

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

                conteudo = cfg.get("mensagem").replace("\u200b", "").replace("\uFEFF", "")

                msg = await thread.send(conteudo)

                if cfg.get("pin"):
                    await msg.pin()

            except Exception as e:
                print(e)

async def setup(bot):
    await bot.add_cog(EasyThreads(bot))
