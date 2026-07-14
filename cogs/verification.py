import discord
from discord.ext import commands
import json
import os

INVITES_FILE = "invites.json"

ROLE_ID = 1524804424352927845  # Cargo que será liberado
INVITE_CHANNEL_ID = 1526281178934542337  # Canal onde será criado o convite


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
            return json.load(f)

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

    def get_user_invites(self, user_id: int):
        return self.data.get(str(user_id), 0)

    def add_invite(self, user_id: int):
        uid = str(user_id)

        if uid not in self.data:
            self.data[uid] = 0

        self.data[uid] += 1
        self.save_data()

    def remove_invite(self, user_id: int):
        uid = str(user_id)

        if uid not in self.data:
            return

        self.data[uid] -= 1

        if self.data[uid] < 0:
            self.data[uid] = 0

        self.save_data()
