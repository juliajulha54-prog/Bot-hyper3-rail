import discord
from discord.ext import commands, tasks
import asyncio
import time

class LockSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.cargo_autorizado_id = 1478835955514343444
        self.canais_liberados = [1471036719028637757]
        self.canais_ignorados = [
            1471028250099716127,
            1471585850696405197,
            1468457145182720010
        ]
        self.cargo_permitido_id = 1478835955514343444
        self.canal_staff_id = 1468439139702669435

        self.collection = bot.db["lock_backup"]

        # 🔥 SISTEMA NOSTALGIA
        self.nostalgia_channel_id = None
        self.msg_count = 0
        self.meta_mensagens = 1800
        self.lock_ativo = False

        self.typing_loop.start()
        self.bot.loop.create_task(self.restaurar_estado())

    async def restaurar_estado(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            data = self.collection.find_one({"guild_id": guild.id})
            if data:
                nostalgia = data.get("nostalgia", {})
                self.nostalgia_channel_id = nostalgia.get("channel_id")
                self.msg_count = nostalgia.get("msg_count", 0)
                self.meta_mensagens = nostalgia.get("meta_mensagens", 1800)
                self.lock_ativo = nostalgia.get("lock_ativo", False)

    def cog_unload(self):
        self.typing_loop.cancel()

    def tem_permissao(self, member):
        return any(role.id == self.cargo_autorizado_id for role in member.roles)

    def barra(self, atual, total):
        tamanho = 20
        progresso = int((atual / total) * tamanho) if total > 0 else 0
        return "█" * progresso + "░" * (tamanho - progresso)

    def salvar_estado(self, guild_id):
        self.collection.update_one(
            {"guild_id": guild_id},
            {"$set": {
                "nostalgia": {
                    "channel_id": self.nostalgia_channel_id,
                    "msg_count": self.msg_count,
                    "meta_mensagens": self.meta_mensagens,
                    "lock_ativo": self.lock_ativo
                }
            }},
            upsert=True
        )

    @tasks.loop(minutes=10)
    async def typing_loop(self):
        if not self.lock_ativo or not self.nostalgia_channel_id:
            return
        channel = self.bot.get_channel(self.nostalgia_channel_id)
        if not channel:
            return
        try:
            async with channel.typing():
                await asyncio.sleep(10)
        except:
            pass

    @commands.command()
    async def lockall(self, ctx):
        if not self.tem_permissao(ctx.author):
            return await ctx.send("❌ | Você não tem permissão para usar isso.")

        self.lock_ativo = True
        self.msg_count = 0

        msg = await ctx.reply("🔒 | Bloqueando todos os canais e cargos...")

        guild = ctx.guild
        cargo_permitido = guild.get_role(self.cargo_permitido_id)
        everyone = guild.default_role

        canais = [
            c for c in guild.channels
            if isinstance(c, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel))
        ]

        # 🔥 BACKUP COMPLETO
        backup_data = {}
        for canal in canais:
            canal_data = {}
            for target, overwrite in canal.overwrites.items():
                canal_data[str(target.id)] = {
                    "allow": overwrite.pair()[0].value,
                    "deny": overwrite.pair()[1].value
                }
            backup_data[str(canal.id)] = canal_data

        self.collection.update_one(
            {"guild_id": guild.id},
            {"$set": {"data": backup_data}},
            upsert=True
        )

        total = len(canais)
        lote_size = 10
        inicio = time.time()
        ultimo_update = 0

        barra = self.barra(0, total)
        await msg.edit(
            content=f"🔒 | Bloqueando todos os canais e cargos...\n"
                    f"[{barra}] 0% (0/{total})\n"
                    f"⏳ Tempo restante: calculando..."
        )

        for i in range(0, total, lote_size):
            lote = canais[i:i+lote_size]
            tasks = []
            for c in lote:
                tasks.append(self.processar_canal(c, guild, ctx, cargo_permitido, everyone))
            await asyncio.gather(*tasks)

            atual = min(i + lote_size, total)
            agora = time.time()

            tempo_passado = agora - inicio
            restante = int((tempo_passado / atual) * (total - atual)) if atual else 0
            minutos = restante // 60
            segundos = restante % 60

            barra = self.barra(atual, total)
            porcentagem = int((atual / total) * 100) if total else 0

            if agora - ultimo_update >= 1:
                await msg.edit(
                    content=f"🔒 | Bloqueando todos os canais e cargos...\n"
                            f"[{barra}] {porcentagem}% ({atual}/{total})\n"
                            f"⏳ Tempo restante: {minutos}m {segundos}s"
                )
                ultimo_update = agora

        try:
            canal_nostalgia = await guild.create_text_channel("☕┃nostalgia")
            self.nostalgia_channel_id = canal_nostalgia.id
            await canal_nostalgia.set_permissions(guild.default_role, view_channel=True, send_messages=True)

            await canal_nostalgia.send("""**## @everyone :coffee: | ...estranho, né?
## O servidor em modo nostalgia <:am_cryingemoji:1473091757519540235> Talvez não seja mais como antes... <:dh_fkAquaCry:1473431628880548032>
## Mas isso não significa que acabou. Sei lá puxa conversa, manda um 'oi'. <a:am_pinguim_oii:1473035478017114318> 
## Às vezes é assim que tudo recomeça.
# :bar_chart: Meta: 1800 mensagens para reabrir automaticamente o servidor. Eu mesma vou reabrir após bater essa meta!**
**-# Se você deseja construir ou cuidar de um servidor... Primeiramente goste de estar ali, goste de ajudar, e não espere recompensas ou vários membros por isso. Se você realmente gosta de ajudar, você se sentirá recompensado de ver as pessoas bem. E se acontecer algo além disso, será lucro.**""")
        except Exception as e:
            print(f"Erro ao criar canal nostalgia: {e}")

        canal_staff = guild.get_channel(self.canal_staff_id)
        if canal_staff:
            try:
                await canal_staff.send("""**> @everyone
:coffee: | Aviso importante para a Staff e "donos"
- Isso não é exatamente um fim…
- - Agora, o que vai acontecer daqui pra frente depende totalmente de vocês... Se vocês realmente quiserem que o servidor continue vivo, vai ser necessário atitude.
- Divulguem, Chamem amigos, Movimentem, façam parcerias... (sempre que puderem ou se quiserem, claro)
- - E principalmente: terminem o que ainda falta.
 Clipes de anime, packs de edição, clips, presets, overlays, fontes, músicas… tudo isso ainda precisa ser organizado e entregue se não, não tem motivo para alguém ficar aqui...
- O servidor tem potencial mas sem esforço, ele morre, assim como já morreu...
- - Se vocês quiserem manter isso de pé, agora é a hora de mostrar se conseguem.
> Ainda não acabou, apenas tentem rapaziada...**""")
            except:
                pass

        self.salvar_estado(guild.id)

        await msg.edit(content="✅ | Todos os canais e cargos bloqueados e privados.\n#HyperLoomvoltaráembreve (ou não) <:dh_fkAquaCry:1473431628880548032>")

    async def processar_canal(self, c, guild, ctx, cargo_permitido, everyone):
        try:
            if c.id == ctx.channel.id or c.id in self.canais_ignorados:
                return

            for cargo in guild.roles:
                if cargo == everyone:
                    continue
                overwrite = c.overwrites_for(cargo)
                overwrite.update(view_channel=False)
                await c.set_permissions(cargo, overwrite=overwrite)

            if c.id in self.canais_liberados and cargo_permitido:
                overwrite = c.overwrites_for(cargo_permitido)
                overwrite.update(view_channel=True)
                await c.set_permissions(cargo_permitido, overwrite=overwrite)

        except Exception as e:
            print(f"Erro no canal {c.name}: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.lock_ativo or message.author.bot:
            return

        if message.channel.id not in (
            self.canais_liberados
            + self.canais_ignorados
            + ([self.nostalgia_channel_id] if self.nostalgia_channel_id else [])
        ):
            return

        self.msg_count += 1
        self.salvar_estado(message.guild.id)

        if self.msg_count >= self.meta_mensagens:
            self.lock_ativo = False

            try:
                await message.channel.send(
                    "@everyone | ☕ ...olha só.\n"
                    "Vocês realmente fizeram acontecer.\n"
                    "O servidor será reaberto."
                )
            except:
                pass

            ctx = await self.bot.get_context(message)
            await self.unlockall(ctx)

    @commands.command()
    async def unlockall(self, ctx):
        if not self.tem_permissao(ctx.author):
            return await ctx.send("❌ | Você não tem permissão para usar isso")

        msg = await ctx.send("🔓 | Desbloqueando todos os canais...")

        guild = ctx.guild
        canais = [
            c for c in guild.channels
            if isinstance(c, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel))
        ]

        data = self.collection.find_one({"guild_id": guild.id})
        if not data:
            return await msg.edit(content="❌ | Nenhum backup encontrado.")

        backup_data = data["data"]

        total = len(canais)
        lote_size = 10
        inicio = time.time()
        ultimo_update = 0

        for i in range(0, total, lote_size):
            lote = canais[i:i+lote_size]
            tasks = [self.restaurar_canal(c, guild, backup_data) for c in lote]
            await asyncio.gather(*tasks)

            atual = min(i + lote_size, total)
            agora = time.time()

            tempo_passado = agora - inicio
            restante = int((tempo_passado / atual) * (total - atual)) if atual else 0
            minutos = restante // 60
            segundos = restante % 60
            barra = self.barra(atual, total)
            porcentagem = int((atual / total) * 100) if total else 0

            if agora - ultimo_update >= 1:
                await msg.edit(
                    content=f"🔓 | Desbloqueando todos os canais...\n"
                            f"[{barra}] {porcentagem}% ({atual}/{total})\n"
                            f"⏳ Tempo restante: {minutos}m {segundos}s"
                )
                ultimo_update = agora

        await msg.edit(content="✅ | Todos os canais foram restaurados com sucesso!")

    async def restaurar_canal(self, c, guild, backup_data):
        try:
            canal_backup = backup_data.get(str(c.id), {})

            for target in list(c.overwrites):
                await c.set_permissions(target, overwrite=None)

            for target_id, perms in canal_backup.items():
                target = guild.get_role(int(target_id)) or guild.get_member(int(target_id))
                if not target:
                    continue

                allow = discord.Permissions(perms["allow"])
                deny = discord.Permissions(perms["deny"])
                overwrite = discord.PermissionOverwrite.from_pair(allow, deny)

                await c.set_permissions(target, overwrite=overwrite)

        except Exception as e:
            print(f"Erro ao restaurar {c.name}: {e}")

async def setup(bot):
    await bot.add_cog(LockSystem(bot))
