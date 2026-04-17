import discord
from discord.ui import View, Select, Button

guild = ctx.guild

cores = [
    r for r in reversed(guild.roles)
    if r.name.startswith("✦") and not r.managed
]

if not cores:
    return await ctx.send("❌ Nenhuma cor encontrada")


def chunk(lista, tamanho):
    return [lista[i:i+tamanho] for i in range(0, len(lista), tamanho)]

paginas = chunk(cores, 8)


# 🔽 SELECT FIXO (sem recriar)
class CorSelect(Select):
    def __init__(self, view):
        self.view_ref = view
        super().__init__(
            placeholder="🎨 Escolha suas cores",
            min_values=1,
            max_values=8,
            options=[]
        )

    async def callback(self, interaction: discord.Interaction):
        roles = [
            interaction.guild.get_role(int(rid))
            for rid in self.values
        ]

        # remove antigas
        for r in cores:
            if r in interaction.user.roles:
                await interaction.user.remove_roles(r)

        # adiciona novas
        await interaction.user.add_roles(*roles)

        await interaction.response.send_message(
            "✅ | Cores atualizadas!",
            ephemeral=True
        )


# ⬅️ ANTERIOR
class PrevButton(Button):
    def __init__(self, view):
        self.view_ref = view
        super().__init__(label="⬅️ Anterior", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page = (self.view_ref.page - 1) % len(paginas)
        self.view_ref.update_select()

        await interaction.response.edit_message(
            embed=self.view_ref.get_embed(),
            view=self.view_ref
        )


# ➡️ PRÓXIMO
class NextButton(Button):
    def __init__(self, view):
        self.view_ref = view
        super().__init__(label="Próximo ➡️", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page = (self.view_ref.page + 1) % len(paginas)
        self.view_ref.update_select()

        await interaction.response.edit_message(
            embed=self.view_ref.get_embed(),
            view=self.view_ref
        )


# ❌ RESET
class ResetButton(Button):
    def __init__(self, view):
        self.view_ref = view
        super().__init__(label="❌ Resetar todas as cores", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "⚠️ Você quer mesmo remover todas as cores?",
            view=ConfirmResetView(),
            ephemeral=True
        )


# ✅ CONFIRMAÇÃO
class ConfirmResetView(View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):

        for r in cores:
            if r in interaction.user.roles:
                await interaction.user.remove_roles(r)

        await interaction.response.edit_message(
            content="🧹 | Todas as cores foram removidas!",
            view=None
        )

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="❎ Cancelado.",
            view=None
        )


# 📦 VIEW LEVE
class CorView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.page = 0

        self.select = CorSelect(self)
        self.prev = PrevButton(self)
        self.next = NextButton(self)
        self.reset = ResetButton(self)

        self.add_item(self.select)
        self.add_item(self.prev)
        self.add_item(self.next)
        self.add_item(self.reset)

        self.update_select()

    def update_select(self):
        pagina = paginas[self.page]

        self.select.options = [
            discord.SelectOption(label=r.name, value=str(r.id))
            for r in pagina
        ]

    def get_embed(self):
        lista = paginas[self.page]

        return discord.Embed(
            title="🎨 Painel de cores",
            description=(
                f"**Página {self.page+1}/{len(paginas)}**\n\n"
                + "\n".join([f"• {r.mention}" for r in lista])
            ),
            color=discord.Color.blurple()
)
