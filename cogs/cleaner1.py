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
        if not conteudo:
            return True

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

        # BOTÕES (igual o seu, mantido)

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
            await i.response.send_message("📩 Envie a nova mensagem (60s)", ephemeral=True)

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

    # ---------------- EVENTO (CORRIGIDO) ----------------

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

            # 🔥 BLOQUEIO DE TEXTO + LINKS
            if not m.attachments and not self.link_permitido(m.content):
                try:
                    await m.delete()
                except:
                    pass
                return

            try:
                nome = cfg.get("nome", "Thread de {user}").replace("{user}", m.author.name)
                thread = await m.create_thread(name=nome)

                conteudo = (cfg.get("mensagem") or "").replace("\u200b", "").replace("\uFEFF", "")

                msg = await thread.send(conteudo)

                if cfg.get("pin"):
                    await msg.pin()

            except Exception as e:
                print(e)

async def setup(bot):
    await bot.add_cog(EasyThreads(bot))
