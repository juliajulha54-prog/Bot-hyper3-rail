import discord  
from discord.ext import commands  
from discord import app_commands  
import uuid  
import re  
  
invite_regex = re.compile(r"(discord\.gg/|discord\.com/invite/)")  
emoji_regex = re.compile(r"<a?:\w+:\d+>")  
  
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

        # 🔥 NOVO BOTÃO (ADICIONADO)
        @discord.ui.button(label="Mensagem (chat)", row=2)
        async def mensagem_chat(self, i: discord.Interaction, b):
            await i.response.send_message(
                "✍️ Envie a nova mensagem no chat (você tem 60s)...",
                ephemeral=True
            )

            def check(m):
                return m.author.id == i.user.id and m.channel.id == i.channel.id

            try:
                msg = await self.cog.bot.wait_for("message", timeout=60, check=check)
            except:
                return await i.followup.send("⏰ Tempo esgotado.", ephemeral=True)

            content = msg.content

            await set_cfg(self.cog.bot, self.config_id, {
                "mensagem": content
            })

            try:
                await msg.delete()
            except:
                pass

            await self.update(i)

            await i.followup.send(
                f"✅ Mensagem atualizada para:\n**{content}**",
                ephemeral=True
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

    # resto do código continua EXATAMENTE igual...
