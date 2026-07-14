import discord
from discord.ext import commands
from discord import app_commands

# IDs fornecidos
ROLE_ID = 1524804424352927845  # ID do cargo que o usuário ganhará
CHANNEL_ID = 1525569173420507216  # ID do canal onde a embed será enviada

# Emojis personalizados para as mensagens e botões
EMOJI_CONVITE = "<:convite:1526352250837143552>"
EMOJI_VERIFY = "<:verify:1526360202197209128>"


class VerificationView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        # timeout=None e custom_id em cada botão garantem a persistência pós-reboot
        super().__init__(timeout=None)
        self.bot = bot

    # Botão com o emoji de Verificação integrado
    @discord.ui.button(
        label="Validar verificação", 
        style=discord.ButtonStyle.green, 
        custom_id="verify_btn",
        emoji=discord.PartialEmoji.from_str(EMOJI_VERIFY)
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        member = interaction.user
        role = guild.get_role(ROLE_ID)
        
        if not role:
            await interaction.followup.send("❌ | O cargo de verificação não foi encontrado. Contate um administrador.", ephemeral=True)
            return
            
        if role in member.roles:
            await interaction.followup.send(f"{EMOJI_VERIFY} | Você já está verificado e possui o cargo!", ephemeral=True)
            return

        cog = self.bot.get_cog("Verification")
        if not cog:
            await interaction.followup.send("❌ | Sistema temporariamente indisponível.", ephemeral=True)
            return
            
        # Busca a quantidade de convites direto no MongoDB (usando await de forma correta)
        invites_count = await cog.get_user_invites(member.id)
        
        if invites_count >= 3:
            try:
                await member.add_roles(role)
                await interaction.followup.send(f"{EMOJI_VERIFY} | **Verificação concluída!** Você convidou {invites_count} pessoas e recebeu o cargo **{role.name}**.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("❌ | Eu não tenho permissão para gerenciar cargos. Verifique se meu cargo está acima do cargo de verificação na lista de cargos do Discord.", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ | Você precisa de 3 convites. No momento, você tem apenas **{invites_count}/3** convites validados.", ephemeral=True)

    # Botão com o emoji de Convite integrado
    @discord.ui.button(
        label="Meus convites", 
        style=discord.ButtonStyle.blurple, 
        custom_id="my_invites_btn",
        emoji=discord.PartialEmoji.from_str(EMOJI_CONVITE)
    )
    async def my_invites(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog("Verification")
        if not cog:
            await interaction.response.send_message("❌ | Sistema temporariamente indisponível.", ephemeral=True)
            return

        invites_count = await cog.get_user_invites(interaction.user.id)
        await interaction.response.send_message(f"{EMOJI_CONVITE} | Você possui atualmente **{invites_count}** convites validados.", ephemeral=True)

    # Botão com o emoji de Link (🔗) integrado
    @discord.ui.button(
        label="Criar convite", 
        style=discord.ButtonStyle.gray, 
        custom_id="create_invite_btn",
        emoji="🔗"
    )
    async def create_invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog("Verification")
        if not cog:
            await interaction.response.send_message(f"{EMOJI_CONVITE} | ❌ Sistema temporariamente indisponível.", ephemeral=True)
            return

        user_id = interaction.user.id
        
        # Verifica se o usuário já tem um convite ativo registrado no cache
        convite_existente = None
        for code, data in cog.invite_cache.items():
            if data["inviter"] == user_id:
                convite_existente = code
                break

        if convite_existente:
            await interaction.response.send_message(
                content=f"⚠️ | Você já possui um convite criado! Para evitar abusos, limitamos a **1 convite por usuário**. Use o seu link:\nhttps://discord.gg/{convite_existente}", 
                ephemeral=True
            )
            return

        try:
            invite = await interaction.channel.create_invite(max_age=0, max_uses=0, unique=True, reason=f"Criado por {interaction.user}")
            
            cog.invite_cache[invite.code] = {
                "uses": invite.uses,
                "inviter": user_id
            }
                
            await interaction.response.send_message(f"🔗 | Aqui está o seu convite exclusivo:\n{invite.url}", ephemeral=True)
        except Exception:
            await interaction.response.send_message("❌ | Não consegui criar um convite neste canal. Certifique-se de que eu tenho permissão para 'Criar Convites'.", ephemeral=True)


class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {}

    # --- Funções do Banco de Dados MongoDB ---

    async def get_user_invites(self, user_id):
        """Busca a quantidade de convites validados de um usuário no MongoDB"""
        try:
            data = await self.bot.db["verification_invites"].find_one({"user_id": str(user_id)})
            if data:
                return data.get("invites_count", 0)
        except Exception as e:
            print(f"Erro ao buscar convites no MongoDB: {e}")
        return 0

    async def update_user_invites(self, user_id, increment_value):
        """Aumenta ou diminui os convites de um usuário no MongoDB"""
        try:
            await self.bot.db["verification_invites"].update_one(
                {"user_id": str(user_id)},
                {"$inc": {"invites_count": increment_value}},
                upsert=True
            )
        except Exception as e:
            print(f"Erro ao atualizar convites no MongoDB: {e}")

    async def get_referred_by(self, member_id):
        """Busca quem convidou o membro recém-chegado no MongoDB"""
        try:
            data = await self.bot.db["verification_referrals"].find_one({"member_id": str(member_id)})
            if data:
                return data.get("inviter_id")
        except Exception as e:
            print(f"Erro ao buscar indicação no MongoDB: {e}")
        return None

    async def set_referred_by(self, member_id, inviter_id):
        """Registra a relação de quem convidou quem no MongoDB"""
        try:
            await self.bot.db["verification_referrals"].update_one(
                {"member_id": str(member_id)},
                {"$set": {"inviter_id": str(inviter_id)}},
                upsert=True
            )
        except Exception as e:
            print(f"Erro ao definir indicação no MongoDB: {e}")

    async def remove_referred_by(self, member_id):
        """Remove a indicação do banco MongoDB e retorna o ID de quem o convidou"""
        try:
            data = await self.bot.db["verification_referrals"].find_one_and_delete({"member_id": str(member_id)})
            if data:
                return data.get("inviter_id")
        except Exception as e:
            print(f"Erro ao remover indicação no MongoDB: {e}")
        return None

    async def cog_load(self):
        # Torna a view persistente registrando-a no bot global e passando o bot
        self.bot.add_view(VerificationView(self.bot))
        self.bot.loop.create_task(self.load_all_invites())

    async def load_all_invites(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                for invite in invites:
                    if invite.inviter:
                        self.invite_cache[invite.code] = {
                            "uses": invite.uses,
                            "inviter": invite.inviter.id
                        }
            except discord.Forbidden:
                print(f"Sem permissão para ler convites no servidor: {guild.name}")

    # --- Eventos de Rastreamento de Convites ---

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if invite.inviter:
            self.invite_cache[invite.code] = {
                "uses": invite.uses,
                "inviter": invite.inviter.id
            }

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        self.invite_cache.pop(invite.code, None)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            current_invites = await member.guild.invites()
            for invite in current_invites:
                cached = self.invite_cache.get(invite.code)
                if cached and invite.uses > cached["uses"]:
                    inviter_id = str(cached["inviter"])
                    member_id = str(member.id)
                    
                    if inviter_id == member_id:
                        break  # Evita autoverificação
                        
                    # Registra no MongoDB
                    await self.set_referred_by(member_id, inviter_id)
                    await self.update_user_invites(inviter_id, 1)
                    
                    # Atualiza o cache temporário local
                    self.invite_cache[invite.code]["uses"] = invite.uses
                    break
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        member_id = str(member.id)
        # Se quem saiu foi convidado por alguém, desconta o ponto no MongoDB
        inviter_id = await self.remove_referred_by(member_id)
        if inviter_id:
            try:
                # Garante que o valor não fique menor que zero na redução
                await self.bot.db["verification_invites"].update_one(
                    {"user_id": str(inviter_id)},
                    [{"$set": {"invites_count": {"$max": [0, {"$subtract": ["$invites_count", 1]}]}}}]
                )
            except Exception as e:
                print(f"Erro ao remover convite no MongoDB: {e}")

    # --- Comando Slash para enviar o Painel ---

    @app_commands.command(name="setup_verificacao", description="Envia a embed de verificação com os botões.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_verificacao(self, interaction: discord.Interaction):
        # Busca o canal específico configurado pelo ID
        channel = self.bot.get_channel(CHANNEL_ID)
        
        if not channel:
            await interaction.response.send_message(f"❌ Não encontrei o canal com o ID `{CHANNEL_ID}`. Verifique as permissões do bot.", ephemeral=True)
            return

        # Descrição exata formatada com os IDs de emojis fornecidos
        descrição_completa = """# <:topic1:1526287141775343656> <:convite:1526352250837143552> Convide 3 pessoas
> Convide 3 pessoas usando seu convite, não importa se são Editores ou não. Após atingir a meta de 3 convites, clique no botão abaixo "Validar verificação".
# <:topicopen:1526287216954052719> <:verify:1526360202197209128> Depois de verificar:
> - :package: Acesso aos presets e project files para AE & AMZ 
> - :clapper: Recursos de edição & Tutoriais:
 CC`S, Packs, Fontes, Overlays, Clipes, Packs de Edit AMV, Pack de Edit woodl e outros, músicas, etc.
> - :tools: Categoria de suporte para editores
> - :fire: Conteúdos & clipes exclusivos
# <:topicopen:1526287216954052719> <:__:1526354605028413440> Como ver seus convites: 
> - Para ver seus convites, clique no botão "Meus convites"
> - Você também poderá, caso queira, criar o seu próprio convite, clicando no botão "Criar convite".
-# <:prints:1526358671691612200> Certifique-se de que realmente mandou o convite para 3 pessoas, você pode, caso queira anexar prints como provas, ou tirar suas dúvidas no tópico abaixo."""

        embed = discord.Embed(
            description=descrição_completa,
            color=discord.Color.blue()
        )
        
        await channel.send(embed=embed, view=VerificationView(self.bot))
        await interaction.response.send_message(f"✅ Embed de verificação configurada e enviada no canal <#{CHANNEL_ID}>!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Verification(bot))
    
