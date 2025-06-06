import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

acertos_file = "acertos.txt"
meta = 530

# View com botão
class AcertoView(discord.ui.View):
    @discord.ui.button(label="Responder", style=discord.ButtonStyle.primary)
    async def responder(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AcertoModal())

# Modal para inserir o valor de acerto
class AcertoModal(discord.ui.Modal, title="Informe seu acerto"):
    acerto = discord.ui.TextInput(label="Quantos de acerto você tem?", placeholder="Ex: 450", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            acerto_valor = int(self.acerto.value.strip())
        except ValueError:
            await interaction.response.send_message("Por favor, insira um número válido.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        username = str(interaction.user)
        salvar_acerto(user_id, username, acerto_valor)

        await interaction.response.send_message(f"Acerto registrado com sucesso: {acerto_valor}", ephemeral=True)

def salvar_acerto(user_id, username, acerto):
    dados = carregar_acertos()
    dados[user_id] = {"username": username, "acerto": acerto}
    with open(acertos_file, "w", encoding="utf-8") as f:
        for uid, info in dados.items():
            f.write(f"{uid};{info['username']};{info['acerto']}\n")

def carregar_acertos():
    dados = {}
    try:
        with open(acertos_file, "r", encoding="utf-8") as f:
            for linha in f:
                partes = linha.strip().split(";")
                if len(partes) == 3:
                    uid, username, acerto = partes
                    dados[uid] = {"username": username, "acerto": int(acerto)}
    except FileNotFoundError:
        pass
    return dados

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

# Comando para enviar pesquisa
@bot.tree.command(name="pesquisa", description="Pergunta de acerto")
@app_commands.checks.has_permissions(administrator=True)
async def pesquisa(interaction: discord.Interaction):
    await interaction.response.send_message("Quantos de acerto você tem?", view=AcertoView())
    await asyncio.sleep(5)
    try:
        await interaction.delete_original_response()
    except discord.NotFound:
        pass

# Comando para mostrar ranking
@bot.tree.command(name="rankacerto", description="Mostra o ranking de acertos")
async def rankacerto(interaction: discord.Interaction):
    dados = carregar_acertos()
    if not dados:
        await interaction.response.send_message("Nenhum dado de acerto encontrado.", ephemeral=True)
        return

    ordenado = sorted(dados.values(), key=lambda x: x["acerto"], reverse=True)
    msg = "**📊 Ranking de Acertos**\n\n"
    for i, info in enumerate(ordenado, start=1):
        status = "✅" if info["acerto"] >= meta else "❌"
        msg += f"**{i}.** {info['username']} - `{info['acerto']}` acerto {status}\n"

    await interaction.response.send_message(msg)

# Caso o usuário não seja administrador
@pesquisa.error
async def pesquisa_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
