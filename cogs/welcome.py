import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp
import io
import random
import json
import os


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # base do projeto (evita erro no Railway)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = os.path.join(self.base_dir, "..")

        # carregar config
        with open(os.path.join(self.base_dir, "config.json"), "r", encoding="utf-8") as f:
            self.config = json.load(f)

    # =========================
    # AVATAR SAFE
    # =========================
    async def pegar_avatar(self, url):
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    return await resp.read()
        except:
            return None

    def escolher_fundo(self):
        fundo = random.choice(self.config["fundos"])
        return os.path.join(self.base_dir, fundo)

    def criar_imagem(self, member, avatar_bytes):
        largura, altura = 900, 300

        fundo = Image.open(self.escolher_fundo()).convert("RGBA")
        fundo = fundo.resize((largura, altura))

        fundo = fundo.filter(ImageFilter.GaussianBlur(1.5))

        overlay = Image.new("RGBA", (largura, altura), (0, 0, 0, 110))
        fundo = Image.alpha_composite(fundo, overlay)

        draw = ImageDraw.Draw(fundo)

        # =========================
        # AVATAR SAFE
        # =========================
        if avatar_bytes:
            avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        else:
            avatar = Image.new("RGBA", (140, 140), (80, 80, 80, 255))

        avatar = avatar.resize((140, 140))

        mask = Image.new("L", avatar.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle((0, 0, 140, 140), 20, fill=255)

        fundo.paste(avatar, (40, 80), mask)
        draw.rounded_rectangle((40, 80, 180, 220), radius=20, outline="white", width=3)

        # =========================
        # FONTES SAFE
        # =========================
        try:
            fonte_path = os.path.join(self.base_dir, self.config["fonte"])
            fonte_titulo = ImageFont.truetype(fonte_path, 55)
            fonte_nome = ImageFont.truetype(fonte_path, 40)
            fonte_tag = ImageFont.truetype(fonte_path, 22)
        except:
            fonte_titulo = ImageFont.load_default()
            fonte_nome = ImageFont.load_default()
            fonte_tag = ImageFont.load_default()

        texto = random.choice(self.config["mensagens"])

        def texto_com_sombra(pos, text, fonte, cor="white"):
            x, y = pos
            draw.text((x + 2, y + 2), text, font=fonte, fill="black")
            draw.text((x, y), text, font=fonte, fill=cor)

        texto_com_sombra((220, 70), texto, fonte_titulo)
        texto_com_sombra((220, 150), member.name, fonte_nome)

        texto_com_sombra((820, 260), "#0", fonte_tag)

        buffer = io.BytesIO()
        fundo.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer

    # =========================
    # EVENTO
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            canal = member.guild.get_channel(self.config["canal_id"])

            if canal is None:
                print("Canal não encontrado.")
                return

            avatar_bytes = await self.pegar_avatar(member.display_avatar.url)
            imagem = self.criar_imagem(member, avatar_bytes)

            file = discord.File(imagem, filename="welcome.png")

            # 👇 SUA MENSAGEM ORIGINAL (NÃO ALTERADA)
            await canal.send(
                content=f"""### > Olá {member.mention}, Boas vindas indo ao Hyper Loom! <:coraohyper:1469892290628550751>
## Estamos com 60 membros atualmente. <:weebyaah:1470084311339368573>
# Antes de tudo, você deve ler as regras do servidor para evitar punições deselegantes.
**__### Você poderá encontrá-las em <#1468502330939932758>! <:h_aquathinker:1470083923710316597>__**""",
                file=file
            )

        except Exception as e:
            print("Erro no welcome:", e)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
