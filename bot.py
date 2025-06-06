import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

acertos_file = "acertos.txt"
META = 530

# Cria o arquivo se não existir
if not os.path.exists(acertos_file):
    with open(acertos_file, "w") as f:
        pass

# Bot online
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")

# Comando /pesquisa
@bot.tree.command(name="pesquisa", description="Faz uma pesquisa sobre acertos")
@app_commands.checks.has_permissions(administrator=True)
async def pesquisa(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Quantos de acerto você tem?",
        view=AcertoButton(),
        ephemeral=False
    )
    # Apaga a mensagem do comando do admin depois de 5 segundos
    try:
        await asyncio.sleep(5)
        await interaction.delete_original_response()
    except:
        pass

# Botão de acerto
class AcertoButton(discord.ui.View):
    @discord.ui.button(label="Responder", style=discord.ButtonStyle.primary)
    async def responder(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Quantos de acerto você tem? (ex: 450)", ephemeral=True)

        def check(m):
            return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)

        try:
            msg = await bot.wait_for("message", timeout=60.0, check=check)
            valor = int(msg.content)

            with open(acertos_file, "a", encoding="utf-8") as f:
                f.write(f"{interaction.user.name}={valor}\n")

            await msg.channel.send("Obrigado! Seu acerto foi registrado ✅")

        except asyncio.TimeoutError:
            await interaction.user.send("⏰ Tempo esgotado. Por favor, tente novamente.")
        except ValueError:
            await interaction.user.send("❌ Valor inválido. Envie apenas números.")

# Comando /rankacerto
@bot.tree.command(name="rankacerto", description="Mostra o ranking de acertos")
@app_commands.checks.has_permissions(administrator=True)
async def rankacerto(interaction: discord.Interaction):
    if not os.path.exists(acertos_file):
        await interaction.response.send_message("Nenhum dado de acerto foi registrado ainda.", ephemeral=True)
        return

    with open(acertos_file, "r", encoding="utf-8") as f:
        dados = [linha.strip().split("=") for linha in f if "=" in linha]

    if not dados:
        await interaction.response.send_message("Nenhum dado válido encontrado.", ephemeral=True)
        return

    # Ordenar
    dados_ordenados = sorted(dados, key=lambda x: int(x[1]), reverse=True)

    acima_meta = [f"✅ **{nome}** - {valor}" for nome, valor in dados_ordenados if int(valor) >= META]
    abaixo_meta = [f"❌ **{nome}** - {valor}" for nome, valor in dados_ordenados if int(valor) < META]

    resultado = "**🏆 Ranking de Acertos**\n\n"
    resultado += "**🔝 Atingiram a meta (530+):**\n" + "\n".join(acima_meta) + "\n\n"
    resultado += "**📉 Ainda não atingiram:**\n" + "\n".join(abaixo_meta)

    await interaction.response.send_message(resultado)

# Iniciar o bot
bot.run(os.getenv("KEY"))
