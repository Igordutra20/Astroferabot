import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
acertos_arquivo = "acertos.txt"
meta = 530

class AcertoView(discord.ui.View):
    @discord.ui.button(label="Responder", style=discord.ButtonStyle.primary)
    async def responder(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.user.send("Quantos de acerto você tem? (ex: 450)")
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não consegui enviar DM para você. Verifique suas configurações de privacidade.",
                ephemeral=True
            )
            return

        await interaction.response.send_message("📩 Verifique sua DM para responder!", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and isinstance(m.channel, discord.DMChannel)

        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
            acertos = int(msg.content.strip())
            nome_usuario = interaction.user.name

            # Atualizar ou adicionar no arquivo
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


@bot.event
async def on_ready():
    print(f"Bot online como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")


@bot.tree.command(name="pesquisa", description="Inicia uma pesquisa de acertos.")
@app_commands.checks.has_permissions(administrator=True)
async def pesquisa(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Quantos de acerto você tem?", 
        view=AcertoView()
    )
    await asyncio.sleep(3000)
    try:
        await interaction.delete_original_response()
    except discord.NotFound:
        pass


@bot.tree.command(name="rankacerto", description="Mostra o ranking de acertos.")
@app_commands.checks.has_permissions(administrator=True)
async def rankacerto(interaction: discord.Interaction):
    if not os.path.exists(acertos_arquivo):
        await interaction.response.send_message("Nenhum dado registrado ainda.")
        return

    with open(acertos_arquivo, "r") as f:
        dados = [linha.strip().split(" = ") for linha in f]
        dados = sorted(dados, key=lambda x: int(x[1]), reverse=True)

    mensagem = "**📊 Ranking de Acertos**\n"
    for i, (nome, acertos) in enumerate(dados, 1):
        status = "✅ Atingiu a meta!" if int(acertos) >= meta else "❌ Abaixo da meta"
        mensagem += f"**{i}. {nome}** - {acertos} ({status})\n"

    await interaction.response.send_message(mensagem)

@pesquisa.error
@rankacerto.error
async def perm_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running.')

def detectar_itens_faltando(image_bytes):
    # Abrir imagem a partir dos bytes recebidos
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    opencv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # Executar OCR com posição dos textos
    data = pytesseract.image_to_data(opencv_img, output_type=pytesseract.Output.DICT, lang='eng')

    resultados = []

    for i in range(len(data["text"])):
        texto = data["text"][i]
        
        # Procurar textos no formato x/y
        if "/" in texto:
            partes = texto.split("/")
            if len(partes) == 2 and partes[0].replace('.', '').isdigit() and partes[1].replace('.', '').isdigit():
                atual = int(partes[0].replace('.', ''))
                total = int(partes[1].replace('.', ''))

                # Coordenadas do texto detectado
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]

                # Recortar a área do texto para verificar a cor
                roi_texto = opencv_img[y:y + h, x:x + w]
                cor_media = cv2.mean(roi_texto)[:3]  # RGB

                # Condição para vermelho (predominância de R, baixa de G e B)
                is_red = cor_media[2] > 140 and cor_media[0] < 100 and cor_media[1] < 100

                if atual < total and is_red:
                    # Recortar a imagem à esquerda do número (onde está o ícone do item)
                    largura_icone = h
                    inicio_x = max(0, x - largura_icone - 10)
                    fim_x = x - 10
                    roi_icone = opencv_img[y:y + h, inicio_x:fim_x]

                    # Converter o ícone recortado para bytes
                    _, buffer = cv2.imencode('.png', roi_icone)
                    icon_image = io.BytesIO(buffer)
                    icon_image.name = f'item_{i}.png'

                    # Adicionar aos resultados
                    resultados.append({
                        "quantidade": f"{atual}/{total}",
                        "imagem_bytes": icon_image
                    })

    return resultados

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), DummyHandler)
    server.serve_forever()

# Iniciar o servidor web falso em segundo plano
threading.Thread(target=run_web_server, daemon=True).start()
# Início do bot com token do ambiente (Render)
bot.run(os.getenv("DISCORD_TOKEN"))
