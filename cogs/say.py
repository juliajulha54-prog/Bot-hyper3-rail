import discord
from discord.ext import commands

STAFF_ROLE_NAMES = ["Administração", "Permissão de Admin", "🔥", "dono", "Sub-Dono"]  # edite aqui

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # CHECAR SE É STAFF
    # =========================
    def is_staff(self, member: discord.Member):
        return any(role.name in STAFF_ROLE_NAMES for role in member.roles)

    # =========================
    # APAGAR COM "0 DELAY"
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.content.startswith((".say", ".sayas")):
            try:
                await message.delete()
            except:
                pass

    # =========================
    # RESOLVER CANAL (MENÇÃO, ID, THREAD)
    # =========================
    def get_channel_from_input(self, ctx, channel_input):
        if isinstance(channel_input, (discord.TextChannel, discord.Thread)):
            return channel_input

        try:
            channel_id = int(channel_input)
            channel = self.bot.get_channel(channel_id)
            return channel
        except:
            return None

    # =========================
    # BUSCAR MENSAGEM POR ID
    # =========================
    async def get_message(self, channel, message_id):
        try:
            return await channel.fetch_message(message_id)
        except:
            return None

    # =========================
    # SAY NORMAL / CANAL / ID / THREAD / REPLY
    # =========================
    @commands.command()
    async def say(self, ctx, *, args=None):

        if not self.is_staff(ctx.author):
            return await ctx.send("❌ Apenas membros da Staff podem usar este comando.", delete_after=5)

        if not args:
            return await ctx.send("❌ Use: `.say [#canal ou ID] <mensagem>`", delete_after=5)

        channel = ctx.channel
        mensagem = args
        reply_msg = None

        parts = args.split(" ")

        # =========================
        # DETECTAR CANAL / THREAD
        # =========================
        if ctx.message.channel_mentions:
            channel = ctx.message.channel_mentions[0]
            parts.pop(0)

        elif parts[0].isdigit():
            resolved = self.get_channel_from_input(ctx, parts[0])
            if resolved:
                channel = resolved
                parts.pop(0)
            else:
                return await ctx.send("❌ Canal inválido ou inacessível.", delete_after=5)

        # =========================
        # DETECTAR REPLY POR ID
        # =========================
        if parts and parts[0].isdigit():
            possible_msg = await self.get_message(channel, int(parts[0]))
            if possible_msg:
                reply_msg = possible_msg
                parts.pop(0)

        mensagem = " ".join(parts)

        if not mensagem:
            return

        if reply_msg:
            await channel.send(mensagem, reference=reply_msg)
        else:
            await channel.send(mensagem)

    # =========================
    # SAY COMO USUÁRIO / CANAL / ID / THREAD / REPLY
    # =========================
    @commands.command()
    async def sayas(self, ctx, membro: discord.Member, *, args=None):

        if not self.is_staff(ctx.author):
            return await ctx.send("❌ Apenas membros da Staff podm usar este comando.", delete_after=5)

        if not args:
            return await ctx.send("❌ Use: `.sayas @user [#canal ou ID] <mensagem>`", delete_after=5)

        channel = ctx.channel
        mensagem = args
        reply_msg = None

        parts = args.split(" ")

        # =========================
        # CANAL / THREAD
        # =========================
        if ctx.message.channel_mentions:
            channel = ctx.message.channel_mentions[0]
            parts.pop(0)

        elif parts[0].isdigit():
            resolved = self.get_channel_from_input(ctx, parts[0])
            if resolved:
                channel = resolved
                parts.pop(0)
            else:
                return await ctx.send("❌ | Canal inválido ou inacessível.", delete_after=5)

        # =========================
        # REPLY
        # =========================
        if parts and parts[0].isdigit():
            possible_msg = await self.get_message(channel, int(parts[0]))
            if possible_msg:
                reply_msg = possible_msg
                parts.pop(0)

        mensagem = " ".join(parts)

        if not mensagem:
            return

        # webhook
        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name="SayWebhook")

        if webhook is None:
            webhook = await channel.create_webhook(name="SayWebhook")

        await webhook.send(
            content=mensagem,
            username=membro.display_name,
            avatar_url=membro.display_avatar.url,
            wait=True
        )

    # =========================
    # ERROS
    # =========================
    @sayas.error
    async def sayas_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("**❌ | Usuário não encontrado.**", delete_after=5)

async def setup(bot):
    await bot.add_cog(Say(bot))
