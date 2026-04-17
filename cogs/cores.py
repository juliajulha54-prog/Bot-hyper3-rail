import discord
from discord.ext import commands
from discord.ui import View, Button, Select


# =========================
# UTIL
# =========================
def get_cores(guild):
    return [
        r for r in reversed(guild.roles)
        if r.name.startswith("✦") and not r.managed
    ]


def chunk(lista, tamanho):
    return [lista[i:i + tamanho] for i in range(0, len(lista), tamanho)]


# =========================
# MAIN PANEL
# =========================
class MainPanel(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="✨ Escolher Cor",
        style=discord.ButtonStyle.secondary,
        custom_id="cores:open"
    )
    async def open(self, interaction: discord.Interaction, button: Button):

        view = ColorPanel(interaction.guild)

        await interaction.response.send_message(
            "🎨 Abrindo seletor de cores...",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(
        label="❌ Resetar cores",
        style=discord.ButtonStyle.danger,
        custom_id="cores:reset_open"
    )
    async def reset(self, interaction: discord.Interaction, button: Button):

        await interaction.response.send_message(
            "⚠️ Tem certeza que deseja remover todas suas cores?",
            view=ConfirmReset(interaction.guild),
            ephemeral=True
        )


# =========================
# COLOR PANEL
# =========================
class ColorPanel(View):
    def __init__(self, guild):
        super().__init__(timeout=None)

        self.guild = guild
        self.cores = get_cores(guild)

        self.paginas = chunk(self.cores, 15)
        self.page = 0

        self.build_ui()

    # =========================
    # UI BUILDER
    # =========================
    def build_ui(self):

        pagina = self.paginas[self.page] if self.paginas else []

        self.clear_items()

        # =========================
        # SELECT
        # =========================
        select = Select(
            placeholder="🎨 Escolha sua cor",
            custom_id="cores:select"
        )

        select.options = [
            discord.SelectOption(label=r.name[:100], value=str(r.id))
            for r in pagina
        ] if pagina else [
            discord.SelectOption(label="Nenhuma cor", value="0")
        ]

        select.callback = self.select_callback

        # =========================
        # BOTÕES DE NAVEGAÇÃO
        # =========================
        prev_button = Button(
            label="⬅️ Anterior",
            style=discord.ButtonStyle.secondary,
            custom_id="cores:prev",
            disabled=(self.page == 0)
        )

        next_button = Button(
            label="Próximo ➡️",
            style=discord.ButtonStyle.secondary,
            custom_id="cores:next",
            disabled=(self.page >= len(self.paginas) - 1)
        )

        prev_button.callback = self.prev_page
        next_button.callback = self.next_page

        # =========================
        # 🔥 BOTÃO FINAL (PÁGINA - NÃO CLICÁVEL)
        # =========================
        page_button = Button(
            label=f"📄 Página {self.page + 1}/{len(self.paginas)}",
            style=discord.ButtonStyle.primary,
            custom_id="cores:page_indicator",
            disabled=True
        )

        # =========================
        # ADD ITEMS (ORDEM CORRETA)
        # =========================
        self.select = select

        self.add_item(select)
        self.add_item(prev_button)
        self.add_item(next_button)
        self.add_item(page_button)

    # =========================
    # SELECT
    # =========================
    async def select_callback(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        value = self.select.values[0]

        if value == "0":
            return await interaction.followup.send("❌ Nenhuma cor disponível", ephemeral=True)

        role = interaction.guild.get_role(int(value))

        cores = get_cores(interaction.guild)

        for r in cores:
            if r in interaction.user.roles:
                await interaction.user.remove_roles(r)

        await interaction.user.add_roles(role)

        await interaction.followup.send(
            f"✅ Cor aplicada: {role.mention}",
            ephemeral=True
        )

    # =========================
    # ANTERIOR
    # =========================
    async def prev_page(self, interaction: discord.Interaction):

        if self.page > 0:
            self.page -= 1

        self.build_ui()

        await interaction.response.edit_message(view=self)

    # =========================
    # PRÓXIMO
    # =========================
    async def next_page(self, interaction: discord.Interaction):

        if self.page < len(self.paginas) - 1:
            self.page += 1

        self.build_ui()

        await interaction.response.edit_message(view=self)


# =========================
# RESET
# =========================
class ConfirmReset(View):
    def __init__(self, guild):
        super().__init__(timeout=30)
        self.guild = guild

    @discord.ui.button(
        label="✅ Confirmar",
        style=discord.ButtonStyle.success,
        custom_id="cores:confirm"
    )
    async def confirm(self, interaction: discord.Interaction, button: Button):

        cores = get_cores(self.guild)

        for r in cores:
            if r in interaction.user.roles:
                await interaction.user.remove_roles(r)

        await interaction.response.edit_message(
            content="🧹 | Suas cores foram removidas!",
            view=None
        )

    @discord.ui.button(
        label="❌ Cancelar",
        style=discord.ButtonStyle.secondary,
        custom_id="cores:cancel"
    )
    async def cancel(self, interaction: discord.Interaction, button: Button):

        await interaction.response.edit_message(
            content="❎ Cancelado.",
            view=None
        )


# =========================
# COG
# =========================
class Cores(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(MainPanel(bot))

    @commands.command()
    async def cores(self, ctx):

        cores = get_cores(ctx.guild)

        embed = discord.Embed(
            title="🎨 Painel de Cores",
            description="\n".join([f"• {r.mention}" for r in cores]) or "Nenhuma cor encontrada",
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed, view=MainPanel(self.bot))


async def setup(bot):
    await bot.add_cog(Cores(bot))
