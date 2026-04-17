import discord
from discord.ext import commands
from datetime import datetime, timezone

class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_badges(self, user: discord.User):
        flags = user.public_flags
        badges = []

        if flags.staff:
            badges.append("👨‍💼 Staff")
        if flags.partner:
            badges.append("🤝 Partner")
        if flags.hypesquad:
            badges.append("🎉 HypeSquad")
        if flags.hypesquad_bravery:
            badges.append("🦁 Bravery")
        if flags.hypesquad_brilliance:
            badges.append("🧠 Brilliance")
        if flags.hypesquad_balance:
            badges.append("⚖️ Balance")
        if flags.bug_hunter:
            badges.append("🐛 Bug Hunter")
        if flags.bug_hunter_level_2:
            badges.append("🐞 Bug Hunter 2")
        if flags.early_supporter:
            badges.append("💎 Early Supporter")
        if flags.verified_bot_developer:
            badges.append("👨‍💻 Dev Verificado")
        if flags.active_developer:
            badges.append("🔥 Active Dev")

        return ", ".join(badges) if badges else "Nenhuma"

    def time_ago(self, dt):
        now = datetime.now(timezone.utc)
        diff = now - dt

        years = diff.days // 365
        months = diff.days // 30
        days = diff.days

        if years >= 1:
            return f"há {years} ano{'s' if years > 1 else ''}"
        elif months >= 1:
            return f"há {months} mês{'es' if months > 1 else ''}"
        else:
            return f"há {days} dia{'s' if days > 1 else ''}"

    @commands.command(name="userinfo", aliases=["ui"])
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user = member

        badges = self.get_badges(user)

        created_ts = int(user.created_at.timestamp())
        created_at = f"<t:{created_ts}:F> ({self.time_ago(user.created_at)})"

        joined_at = "Desconhecido"
        if member.joined_at:
            joined_ts = int(member.joined_at.timestamp())
            joined_at = f"<t:{joined_ts}:F> ({self.time_ago(member.joined_at)})"

        embed = discord.Embed(
            title="📌 Informações do Usuário",
            color=discord.Color.blurple()
        )

        embed.set_author(
            name=user.name,  # 👈 username novo
            icon_url=user.display_avatar.url,
            url=f"https://discord.com/users/{user.id}"
        )

        embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(
            name="🎖️ Insígnias do Discord",
            value=badges,
            inline=False
        )

        embed.add_field(
            name="🆔 ID do Discord",
            value=f"`{user.id}`",
            inline=True
        )

        embed.add_field(
            name="🏷️ Nome de usuário",
            value=f"`{user.name}`",
            inline=True
        )

        embed.add_field(
            name="📅 Data de criação da conta",
            value=created_at,
            inline=False
        )

        embed.add_field(
            name="📥 Entrou no servidor",
            value=joined_at,
            inline=False
        )

        embed.set_footer(
            text=f"Solicitado por {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(UserInfo(bot))
