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
