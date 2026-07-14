import discord
from discord.ext import commands
import json
import os

INVITES_FILE = "invites.json"

ROLE_ID = 1524804424352927845
INVITE_CHANNEL_ID = 1526281178934542337


class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}
        self.data = self.load_data()

    def load_data(self):
        if not os.path.exists(INVITES_FILE):
            with open(INVITES_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)

        with open(INVITES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {}

        return data

    def save_data(self):
        with open(INVITES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    async def cache_invites(self):
        self.invites.clear()

        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except discord.Forbidden:
                pass

    def ensure_user(self, user_id: int):
        uid = str(user_id)

        if uid not in self.data:
            self.data[uid] = {
                "invited": []
            }

    def add_invited_member(self, inviter_id: int, member_id: int):
        self.ensure_user(inviter_id)

        invited = self.data[str(inviter_id)]["invited"]

        if member_id not in invited:
            invited.append(member_id)
            self.save_data()

    def remove_invited_member(self, inviter_id: int, member_id: int):
        self.ensure_user(inviter_id)

        invited = self.data[str(inviter_id)]["invited"]

        if member_id in invited:
            invited.remove(member_id)
            self.save_data()

    def get_invites(self, user_id: int):
        self.ensure_user(user_id)
        return len(self.data[str(user_id)]["invited"])

    def get_invited_members(self, user_id: int):
        self.ensure_user(user_id)
        return self.data[str(user_id)]["invited"]

    def find_inviter(self, member_id: int):
        for inviter_id, info in self.data.items():
            if member_id in info.get("invited", []):
                return int(inviter_id)
        return None

    @commands.Cog.listener()
    async def on_ready(self):
        await self.cache_invites()

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        try:
            self.invites[invite.guild.id] = await invite.guild.invites()
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        try:
            self.invites[invite.guild.id] = await invite.guild.invites()
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

        previous_invites = self.invites.get(guild.id, [])

        used_invite = None

        for current in current_invites:
            old = discord.utils.get(previous_invites, code=current.code)

            if old and current.uses > old.uses:
                used_invite = current
                break

        self.invites[guild.id] = current_invites

        if used_invite is None:
            return

        inviter = used_invite.inviter

        if inviter is None or inviter.bot:
            return

        if inviter.id == member.id:
            return

        self.add_invited_member(inviter.id, member.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        inviter_id = self.find_inviter(member.id)

        if inviter_id:
            self.remove_invited_member(inviter_id, member.id)

        try:
            self.invites[member.guild.id] = await member.guild.invites()
        except discord.Forbidden:
            pass
