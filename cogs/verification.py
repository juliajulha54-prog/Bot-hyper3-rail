import discord
from discord.ext import commands
import json
import os

INVITES_FILE = "invites.json"

ROLE_ID = 1524804424352927845
INVITE_CHANNEL_ID = 1526281178934542337
REQUIRED_INVITES = 3


class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.invites_cache: dict[int, list[discord.Invite]] = {}
        self.data = self.load_data()

    def load_data(self):
        if not os.path.exists(INVITES_FILE):
            with open(INVITES_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "users": {},
                        "members": {}
                    },
                    f,
                    indent=4
                )

        with open(INVITES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "users" not in data:
            data["users"] = {}

        if "members" not in data:
            data["members"] = {}

        return data

    def save_data(self):
        with open(INVITES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def ensure_user(self, user_id: int):
        uid = str(user_id)

        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "invited": [],
                "verified": False
            }

    def get_user(self, user_id: int):
        self.ensure_user(user_id)
        return self.data["users"][str(user_id)]

    def get_invites(self, user_id: int):
        return len(self.get_user(user_id)["invited"])

    def is_verified(self, user_id: int):
        return self.get_user(user_id)["verified"]

    def set_verified(self, user_id: int):
        self.ensure_user(user_id)
        self.data["users"][str(user_id)]["verified"] = True
        self.save_data()

    def add_invite(self, inviter_id: int, member_id: int):
        self.ensure_user(inviter_id)

        invited = self.data["users"][str(inviter_id)]["invited"]

        if member_id not in invited:
            invited.append(member_id)

        self.data["members"][str(member_id)] = inviter_id

        self.save_data()

    def remove_invite(self, member_id: int):
        mid = str(member_id)

        if mid not in self.data["members"]:
            return

        inviter_id = str(self.data["members"][mid])

        if inviter_id in self.data["users"]:
            invited = self.data["users"][inviter_id]["invited"]

            if member_id in invited:
                invited.remove(member_id)

        del self.data["members"][mid]

        self.save_data()

    async def cache_invites(self):
        self.invites_cache.clear()

        for guild in self.bot.guilds:
            try:
                self.invites_cache[guild.id] = await guild.invites()
            except discord.Forbidden:
                pass
    @commands.Cog.listener()
    async def on_ready(self):
        await self.cache_invites()

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        try:
            self.invites_cache[invite.guild.id] = await invite.guild.invites()
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        try:
            self.invites_cache[invite.guild.id] = await invite.guild.invites()
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        guild = member.guild

        try:
            current_invites = await guild.invites()
        except discord.Forbidden:
            return

        previous_invites = self.invites_cache.get(guild.id, [])

        used_invite = None

        for invite in current_invites:
            old = discord.utils.get(previous_invites, code=invite.code)

            if old and invite.uses > old.uses:
                used_invite = invite
                break

        self.invites_cache[guild.id] = current_invites

        if used_invite is None:
            return

        inviter = used_invite.inviter

        if inviter is None:
            return

        if inviter.bot:
            return

        if inviter.id == member.id:
            return

        self.add_invite(inviter.id, member.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return

        self.remove_invite(member.id)

        try:
            self.invites_cache[member.guild.id] = await member.guild.invites()
        except discord.Forbidden:
            pass

    async def give_role(self, member: discord.Member):
        role = member.guild.get_role(ROLE_ID)

        if role is None:
            return False

        if role in member.roles:
            return True

        try:
            await member.add_roles(role, reason="Verificação por convites")
            self.set_verified(member.id)
            return True
        except discord.Forbidden:
            return False

    async def create_user_invite(self, guild: discord.Guild):
        channel = guild.get_channel(INVITE_CHANNEL_ID)

        if channel is None:
            return None

        try:
            invite = await channel.create_invite(
                max_age=0,
                max_uses=0,
                unique=True,
                reason="Sistema de verificação"
            )
            return invite
        except discord.Forbidden:
            return None
