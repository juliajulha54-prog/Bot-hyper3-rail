import discord
from discord.ext import commands

class Cleaner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 📋 LISTA DE CANAIS MONITORADOS
        # Adicione os IDs de todos os canais onde o bot deve apagar mensagens não permitidas
        self.canais_permitidos = [
            1486826627655663687
            # 123456789012345678,  <- Exemplo de como adicionar mais canais
            # 987654321098765432
        ]
        
        # 🔗 LINKS AUTORIZADOS
        self.links_autorizados = [
            "mega.nz",
            "drive.google.com",
            "tiktok.com",
            "streamable.com",
            "cdn.nsb.gg"
        ]

    def link_permitido(self, conteudo: str) -> bool:
        conteudo = conteudo.lower()

        # Bloqueia convites de Discord imediatamente
        if "discord.gg" in conteudo or "discord.com/invite" in conteudo:
            return False

        # Verifica se há links e se algum deles está na lista de autorizados
        if "http://" in conteudo or "https://" in conteudo:
            return any(link in conteudo for link in self.links_autorizados)

        return False

    def apenas_anexo(self, message: discord.Message) -> bool:
        # Retorna True se a mensagem tiver pelo menos 1 arquivo/imagem anexado
        return len(message.attachments) > 0

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignora mensagens enviadas por bots (incluindo o próprio bot)
        if message.author.bot:
            return

        # Verifica se a mensagem foi enviada em um dos canais da lista
        if message.channel.id in self.canais_permitidos:
            
            # A mensagem é permitida se tiver anexo OU se contiver um link autorizado
            permitido = self.apenas_anexo(message) or self.link_permitido(message.content)

            # Se não for permitida (texto puro, figurinha, emoji, etc), ela é deletada
            if not permitido:
                try:
                    await message.delete()
                except discord.Forbidden:
                    print(f"⚠️ Erro: O bot não tem permissão de 'Gerenciar Mensagens' no canal {message.channel.name} (ID: {message.channel.id})")
                except discord.HTTPException as e:
                    print(f"⚠️ Erro no Discord ao tentar deletar mensagem: {e}")

# Função obrigatória para carregar a Cog no setup_hook
async def setup(bot):
    await bot.add_cog(Cleaner(bot))
                
