import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
acertos_arquivo = "acertos.txt"

# Sincroniza comandos ao iniciar
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")

# VIEW com o botão
class AcertoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Responder", style=discord.ButtonStyle.primary)
async def responder(self, interaction: discord.Interaction, button: discord.ui.Button):
    try:
        await interaction.user.send("Quantos de acerto você tem? (ex: 450)")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Não consegui enviar DM para você. Verifique suas configurações de privacidade.", ephemeral=True)
        return

    await interaction.response.send_message("📩 Verifique sua DM para responder!", ephemeral=True)

    def check(m):
        return m.author.id == interaction.user.id and isinstance(m.channel, discord.DMChannel)

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        acertos = int(msg.content.strip())
        nome_usuario = interaction.user.name

        # Atualiza ou adiciona no arquivo
        novos_dados = []
        atualizado = False

        if os.path.exists(acertos_arquivo):
            with open(acertos_arquivo, "r") as f:
                for linha in f:
                    nome, valor = linha.strip().split(" = ")
                    if nome == nome_usuario:
                        novos_dados.append(f"{nome_usuario} = {acertos}")
                        atualizado = True
                    else:
                        novos_dados.append(f"{nome} = {valor}")

        if not atualizado:
            novos_dados.append(f"{nome_usuario} = {acertos}")

        with open(acertos_arquivo, "w") as f:
            f.write("\n".join(novos_dados))

        await msg.channel.send(f"✅ Seus acertos ({acertos}) foram registrados com sucesso!")

    except asyncio.TimeoutError:
        await interaction.user.send("⏰ Tempo esgotado para responder.")
# Comando /pesquisa
@bot.tree.command(name="pesquisa", description="Inicia a pesquisa de acertos")
async def pesquisa(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você não tem permissão para usar esse comando.", ephemeral=True)
        return

    await interaction.response.defer(thinking=False)

    # Apaga a mensagem original do comando após 5 segundos
    try:
        await interaction.channel.send("📊 **Quantos de acerto você tem?**", view=AcertoView())
        await asyncio.sleep(5)
        await interaction.delete_original_response()
    except:
        pass

# Comando /rankacerto
@bot.tree.command(name="rankacerto", description="Mostra o ranking de acertos")
async def rankacerto(interaction: discord.Interaction):
    if not os.path.exists(acertos_arquivo):
        await interaction.response.send_message("Nenhum acerto registrado ainda.")
        return

    with open(acertos_arquivo, "r") as f:
        dados = [linha.strip().split(" = ") for linha in f if " = " in linha]
        dados = sorted(dados, key=lambda x: int(x[1]), reverse=True)

    texto_rank = "**🏆 Ranking de Acertos (meta: 530)**\n\n"
    for i, (nome, valor) in enumerate(dados, start=1):
        status = "✅ 530+" if int(valor) >= 530 else "❌ 530+"
        texto_rank += f"{i}. **{nome}** — {valor} acertos {status}\n"

    await interaction.response.send_message(texto_rank)

# Inicia o bot usando token do Render
bot.run(os.environ["DISCORD_TOKEN"])
