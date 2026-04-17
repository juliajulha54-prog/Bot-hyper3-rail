import discord
from discord.ext import commands
import asyncio
import os
from pymongo import MongoClient

# ===============================
# CONFIGURAÇÕES
# ===============================
DONO_ID = [1473488490795896997, 569633804537430036]

PARTICIPANTES = [
    "kerb","mendes","Lima","Dan",
    "fis","Retuurn","Geraldão"
]

lock = asyncio.Lock()

# ===============================
# MONGO
# ===============================
client = MongoClient(os.getenv("MONGO_URI"))
db = client["bot"]
votacoes_db = db["votacoes"]

# ===============================
# AUX
# ===============================
def chave(a,b):
    return f"{a}_vs_{b}"

# ===============================
# VIEW
# ===============================
class VotacaoView(discord.ui.View):
    def __init__(self, cog, a, b):
        super().__init__(timeout=None)
        self.cog = cog
        self.a = a
        self.b = b
        self.confronto = chave(a,b)

        for participante, style in [(a, discord.ButtonStyle.primary), (b, discord.ButtonStyle.danger)]:
            botao = discord.ui.Button(
                label=f"Votar no participante {participante}",
                style=style,
                custom_id=f"vote|{self.confronto}|{participante}"
            )
            botao.callback = self.callback
            self.add_item(botao)

    async def callback(self, interaction: discord.Interaction):
        participante = interaction.data["custom_id"].split("|")[2]
        confronto = interaction.data["custom_id"].split("|")[1]

        async with lock:
            votacao = votacoes_db.find_one({"_id": confronto})
            if not votacao:
                return await interaction.response.send_message("❌ | Esta votação não existe.", ephemeral=True)
            if votacao.get("encerrada"):
                return await interaction.response.send_message("❌ | Esta votação já foi encerrada.", ephemeral=True)

            user_id = str(interaction.user.id)
            if user_id in votacao["votos"]:
                return await interaction.response.send_message("❌ | Você já votou neste confronto.", ephemeral=True)

            votacoes_db.update_one(
                {"_id": confronto},
                {
                    "$set": {f"votos.{user_id}": {"id": user_id, "nome": str(interaction.user), "voto": participante}},
                    "$inc": {f"contagem.{participante}": 1}
                }
            )

        await interaction.response.send_message(f"✅ | Você votou em **{participante}**.", ephemeral=True)

# ===============================
# COG
# ===============================
class Votacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        for v in votacoes_db.find():
            a, b = v["participantes"]
            self.bot.add_view(VotacaoView(self, a, b))

    # ===============================
    # ABRIR VOTAÇÃO
    # ===============================
    @commands.command(name="votação")
    async def abrir(self, ctx, a:str, _, b:str):
        if a not in PARTICIPANTES or b not in PARTICIPANTES:
            return await ctx.reply("❌ | Um dos participantes não existe.")
        async with lock:
            confronto = chave(a,b)
            if votacoes_db.find_one({"_id": confronto}):
                return await ctx.reply("❌ | Essa votação já existe.")

            votacoes_db.insert_one({
                "_id": confronto,
                "participantes": [a,b],
                "votos": {},
                "contagem": {a:0, b:0},
                "encerrada": False
            })

        embed = discord.Embed(
            title="🗳️ Votação aberta",
            description=f"**{a} 🆚 {b}**\n\nClique para votar.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=VotacaoView(self, a, b))

    # ===============================
    # FECHAR VOTAÇÃO
    # ===============================
    @commands.command()
    async def fechar(self, ctx, a:str, _, b:str):
        async with lock:
            confronto = chave(a,b)
            votacao = votacoes_db.find_one({"_id": confronto})
            if not votacao:
                return await ctx.reply("❌ | Não existe votação.")
            if votacao.get("encerrada"):
                return await ctx.reply("❌ | Já encerrada.")

            contagem = votacao["contagem"]
            vencedor = max(contagem, key=contagem.get)
            texto = "\n".join([f"**{k}**: {v}" for k,v in contagem.items()])

            votacoes_db.update_one({"_id": confronto}, {"$set": {"encerrada": True}})

        embed = discord.Embed(
            title="🏆 Votação encerrada",
            description=f"Vencedor: **{vencedor}**",
            color=discord.Color.gold()
        )
        embed.add_field(name="📊 Resultado final", value=texto)
        await ctx.send(embed=embed)

    # ===============================
    # MOSTRAR VOTAÇÃO
    # ===============================
    @commands.command()
    async def mostrar(self, ctx, a:str, _, b:str):
        confronto = chave(a,b)
        votacao = votacoes_db.find_one({"_id": confronto})
        if not votacao:
            return await ctx.reply("❌ | Não existe votação.")

        embed = discord.Embed(
            title="🗳️ Votação",
            description=f"**{a} 🆚 {b}**\n\nClique para votar.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=VotacaoView(self, a, b))

    # ===============================
    # VOTOS (LÍDER NO TOPO)
    # ===============================
    @commands.command()
    async def votos(self, ctx):
        votacoes = list(votacoes_db.find())
        if not votacoes:
            return await ctx.reply("Nenhuma votação.")

        embed = discord.Embed(title="📊 Contagem de votos", color=discord.Color.green())
        for v in votacoes:
            a, b = v["participantes"]
            contagem = v["contagem"]
            ordenado = sorted(contagem.items(), key=lambda x: x[1], reverse=True)
            lider = ordenado[0][0]
            status = "🔒 Encerrada" if v.get("encerrada") else "🟢 Ativa"
            texto = f"👑 Líder: **{lider}**\nStatus: {status}\n\n"
            for nome,votos in ordenado:
                texto += f"**{nome}**: {votos} votos\n"
            embed.add_field(name=f"{a} 🆚 {b}", value=texto, inline=False)
        await ctx.reply(embed=embed)

    # ===============================
    # REINICIAR VOTAÇÃO (ESTILO JSON ANTIGO)
    # ===============================
    @commands.command()
    async def reiniciar(self, ctx, a:str, _, b:str):
        if ctx.author.id not in DONO_ID:
            return await ctx.reply("❌ | Apenas o organizador pode reiniciar a votação.")

        async with lock:
            confronto = chave(a,b)
            votos_iniciais = {}
            contagem_inicial = {a:0, b:0}

            # Exemplo específico Retuurn vs Geraldão
            if {a,b} == {"Retuurn","Geraldão"}:
                contagem_inicial["Retuurn"] = 14
                contagem_inicial["Geraldão"] = 13
                for i in range(1,15):
                    votos_iniciais[f"retuurn_{i}"] = {"id":f"retuurn_{i}","nome":f"Voto{i}","voto":"Retuurn"}
                for i in range(1,14):
                    votos_iniciais[f"geraldao_{i}"] = {"id":f"geraldao_{i}","nome":f"Voto{i}","voto":"Geraldão"}

            votacoes_db.replace_one(
                {"_id": confronto},
                {
                    "_id": confronto,
                    "participantes": [a,b],
                    "votos": votos_iniciais,
                    "contagem": contagem_inicial,
                    "encerrada": True
                },
                upsert=True
            )

        await ctx.reply(f"✅ | Votação **{a} vs {b}** reiniciada com os votos do JSON antigo!")

    # ===============================
    # RESET TOTAL
    # ===============================
    @commands.command()
    async def reset(self, ctx):
        if ctx.author.id not in DONO_ID:
            return await ctx.reply("❌ | Apenas o organizador pode resetar.")
        async with lock:
            votacoes_db.delete_many({})
        await ctx.reply("✅ | Todas as votações foram resetadas!")

# ===============================
# SETUP
# ===============================
async def setup(bot):
    await bot.add_cog(Votacao(bot))
