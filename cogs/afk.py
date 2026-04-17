import discord
from discord.ext import commands
import time
import random

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}
        self.cooldown = {}

        self.frases = [
            "Para de chamar ele 😭",
            "<:dh_fkAquaCry:1473431628880548032> | Hmph! Ele nem tá aqui agora! ",
            "Você não viu que ele está ausente?! <:dh_fkAquaCry:1473431628880548032>",
            "Para de insistir! Ele foi embora 😭",
            "Acho melhor esperar... ou não 😳",
            "Ele sumiu.. Igual minhas responsabilidades 😅"
        ]

    def format_time(self, seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60

        parts = []
        if h > 0:
            parts.append(f"{h}h")
        if m > 0:
            parts.append(f"{m}m")
        if s > 0:
            parts.append(f"{s}s")

        return " ".join(parts) if parts else "0s"

    @commands.command()
    async def afk(self, ctx, *, motivo="Sem motivo."):
        data = {
            "reason": motivo,
            "time": time.time(),
            "username": str(ctx.author),
            "dm_count": 0  # 👈 NOVO
        }

        self.afk_users[ctx.author.id] = data

        self.bot.db.afk.update_one(
            {"_id": ctx.author.id},
            {"$set": data},
            upsert=True
        )

        # 🏷️ ADICIONAR [AFK] NO NICK
        try:
            if isinstance(ctx.author, discord.Member):
                if not ctx.author.display_name.startswith("[AFK]"):
                    await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}")
        except:
            pass

        await ctx.reply(
            f"**<:aquaasleep:1473432813910097922> | {ctx.author.mention} Agora você está AFK...**\n"
            f"**✨ | Motivo: {motivo}**"
        )

    @commands.Cog.listener()
    async def on_ready(self):
        for data in self.bot.db.afk.find():
            self.afk_users[data["_id"]] = data

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)
        if ctx.command:
            return

        user_id = message.author.id

        # ✅ REMOVE AFK
        if user_id in self.afk_users:
            data = self.afk_users.pop(user_id)
            tempo = self.format_time(time.time() - data["time"])

            self.bot.db.afk.delete_one({"_id": user_id})

            # 🔄 REMOVER [AFK] DO NICK
            try:
                if isinstance(message.author, discord.Member):
                    if message.author.display_name.startswith("[AFK] "):
                        new_nick = message.author.display_name.replace("[AFK] ", "", 1)
                        await message.author.edit(nick=new_nick)
            except:
                pass

            await message.channel.send(
                f"**<:h_heartgirl:1470084129499512846> | Bem-vindo de volta, {message.author.mention}!**\n"
                f"**Você ficou AFK por {tempo}... senti sua falta! <:dh_fkAquaCry:1473431628880548032>**"
            )

        # ✅ MENÇÃO AFK
        if message.mentions:
            for user in message.mentions:
                if user.id in self.afk_users:

                    now = time.time()
                    last = self.cooldown.get(message.channel.id, 0)

                    if now - last < 3:
                        return

                    self.cooldown[message.channel.id] = now

                    data = self.afk_users[user.id]
                    tempo = self.format_time(time.time() - data["time"])
                    frase = random.choice(self.frases)

                    # 📩 DM PARA O AFK (LIMITADA A 3)
                    try:
                        db_data = self.bot.db.afk.find_one({"_id": user.id})

                        if db_data:
                            dm_count = db_data.get("dm_count", 0)

                            if dm_count < 3:
                                await user.send(
                                    f"**<:aquaasleep:1473432813910097922> | Opa! `{message.author}` te mencionou no servidor {message.guild.name}**\n"
                                    f"**👀 | Mensagem: {message.content}**"
                                )

                                self.bot.db.afk.update_one(
                                    {"_id": user.id},
                                    {"$inc": {"dm_count": 1}}
                                )
                    except:
                        pass

                    await message.reply(
                        f"**<:aquaasleep:1473432813910097922> | Ei Ei... `{user.name}` está AFK!**\n"
                        f"**✨ | Motivo: {data['reason']}**\n"
                        f"**⏳ | Tempo: {tempo}**\n"
                        f"**{frase}**"
                    )

        await self.bot.process_commands(message)


async def setup(bot):
    await bot.add_cog(AFK(bot))
