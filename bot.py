import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = False
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
acertos_arquivo = "acertos.txt"
META_ACERTO = 530


class AcertoView(discord.ui.View):
    @discord.ui.button(label="Responder", style=discord.ButtonStyle.primary)
    async def responder(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Quantos de acerto você tem? (ex: 450)", ephemeral=True)

        def check(m):
            return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)

        try:
            msg = await bot.wait_for("message", timeout=60.0, check=check)
            try:
                valor = int(msg.content)
                salvar_acerto(interaction.user, valor)
                await msg.channel.send(f"Acerto registrado: {valor}")
            except ValueError:
                await msg.channel.send("Por favor, envie apenas números.")
        except asyncio.TimeoutError:
            await interaction.user.send("Tempo esgotado para responder.")


def salvar_acerto(user, valor):
    dados = {}
    try:
        with open(acertos_arquivo, "r") as f:
            for linha in f:
                nome, val = linha.strip().split(" = ")
                dados[nome] = int(val)
    except FileNotFoundError:
        pass

    dados[str(user)] = valor

    with open(acertos_arquivo, "w") as f:
        for nome, val in dados.items():
            f.write(f"{nome} = {val}\n")


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online como {bot.user}")


@bot.tree.command(name="pesquisa", description="Inicia a pesquisa de acerto")
@app_commands.checks.has_permissions(administrator=True)
async def pesquisa(interaction: discord.Interaction):
    # Defer para que possamos deletar a mensagem original do comando depois
    await interaction.response.defer(ephemeral=True)

    # Envia a mensagem com o botão no canal
    await interaction.channel.send("Quantos de acerto você tem?", view=AcertoView())

    # Espera 5 segundos e deleta a mensagem original do comando
    await asyncio.sleep(5)
    try:
        await interaction.delete_original_response()
    except:
        pass


@bot.tree.command(name="rankacerto", description="Mostra o ranking de acerto")
async def rankacerto(interaction: discord.Interaction):
    try:
        with open(acertos_arquivo, "r") as f:
            dados = [linha.strip().split(" = ") for linha in f]
            dados = sorted(dados, key=lambda x: int(x[1]), reverse=True)

        ranking = ""
        for nome, valor in dados:
            status = "✅ META ATINGIDA" if int(valor) >= META_ACERTO else "❌ FALTA"
            ranking += f"**{nome}** — {valor} de acerto {status}\n"

        await interaction.response.send_message("📊 **Ranking de Acertos:**\n\n" + ranking)
    except FileNotFoundError:
        await interaction.response.send_message("Nenhum dado de acerto encontrado ainda.")


@pesquisa.error
async def pesquisa_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)

bot.run(os.getenv("DISCORD_TOKEN"))
