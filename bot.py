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
bot.requisicoes_pendentes = {}

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

class RequisicaoView(discord.ui.View):
    def __init__(self, requisicao_id):
        super().__init__()
        self.requisicao_id = requisicao_id

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.permissions.administrator for role in interaction.user.roles):
            await interaction.response.send_message("❌ Apenas administradores podem aprovar requisições.", ephemeral=True)
            return
        
        requisicao = bot.requisicoes_pendentes.get(self.requisicao_id)
        if not requisicao:
            await interaction.response.send_message("❌ Requisição não encontrada ou já processada.", ephemeral=True)
            return
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = f"✅ {embed.title} (Aprovado)"
        
        await interaction.message.edit(embed=embed, view=None)
        
        try:
            user = await bot.fetch_user(requisicao['user_id'])
            await user.send("✅ Sua requisição foi aprovada pelos administradores!")
        except discord.Forbidden:
            pass
        
        del bot.requisicoes_pendentes[self.requisicao_id]
        await interaction.response.send_message("✅ Requisição aprovada com sucesso!", ephemeral=True)

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.danger)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.permissions.administrator for role in interaction.user.roles):
            await interaction.response.send_message("❌ Apenas administradores podem recusar requisições.", ephemeral=True)
            return
        
        requisicao = bot.requisicoes_pendentes.get(self.requisicao_id)
        if not requisicao:
            await interaction.response.send_message("❌ Requisição não encontrada ou já processada.", ephemeral=True)
            return
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = f"❌ {embed.title} (Recusado)"
        
        await interaction.message.edit(embed=embed, view=None)
        
        try:
            user = await bot.fetch_user(requisicao['user_id'])
            await user.send("❌ Sua requisição foi recusada pelos administradores.")
        except discord.Forbidden:
            pass
        
        del bot.requisicoes_pendentes[self.requisicao_id]
        await interaction.response.send_message("✅ Requisição recusada com sucesso!", ephemeral=True)

@bot.tree.command(name="requisicao", description="Solicitar itens que faltam")
async def requisicao(interaction: discord.Interaction):
    try:
        await interaction.user.send(
            "📸 Por favor, envie uma imagem com os itens que você está verificando.\n"
            "Certifique-se de que os números estão visíveis e legíveis.\n\n"
            "O bot irá detectar automaticamente os itens que faltam (em vermelho)."
        )
        await interaction.response.send_message(
            "📩 Verifique suas mensagens diretas! Envie a imagem lá.", 
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Não consegui enviar mensagem direta para você. Verifique suas configurações de privacidade.",
            ephemeral=True
        )

def detectar_itens_faltando(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    opencv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    data = pytesseract.image_to_data(opencv_img, output_type=pytesseract.Output.DICT, lang='eng')
    resultados = []

    for i in range(len(data["text"])):
        texto = data["text"][i]
        
        if "/" in texto:
            partes = texto.split("/")
            if len(partes) == 2 and partes[0].replace('.', '').isdigit() and partes[1].replace('.', '').isdigit():
                atual = int(partes[0].replace('.', ''))
                total = int(partes[1].replace('.', ''))

                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]

                roi_texto = opencv_img[y:y + h, x:x + w]
                cor_media = cv2.mean(roi_texto)[:3]
                is_red = cor_media[2] > 140 and cor_media[0] < 100 and cor_media[1] < 100

                if atual < total and is_red:
                    largura_icone = h
                    inicio_x = max(0, x - largura_icone - 10)
                    fim_x = x - 10
                    roi_icone = opencv_img[y:y + h, inicio_x:fim_x]

                    _, buffer = cv2.imencode('.png', roi_icone)
                    icon_image = io.BytesIO(buffer)
                    icon_image.name = f'item_{i}.png'

                    resultados.append({
                        "quantidade": f"{atual}/{total}",
                        "imagem_bytes": icon_image
                    })

    return resultados

async def processar_requisicao(message, attachment):
    try:
        image_bytes = await attachment.read()
        itens_faltando = detectar_itens_faltando(image_bytes)
        
        if not itens_faltando:
            await message.channel.send("✅ Todos os itens parecem estar completos!")
            return
        
        embed = discord.Embed(
            title=f"Requisição de {message.author.display_name}",
            description="⚠️ Itens faltando detectados:",
            color=discord.Color.orange()
        )
        
        for i, item in enumerate(itens_faltando, 1):
            embed.add_field(
                name=f"Item {i}",
                value=f"Quantidade: {item['quantidade']}",
                inline=False
            )
        
        first_image = itens_faltando[0]['imagem_bytes']
        first_image.seek(0)
        file = discord.File(first_image, filename="item.png")
        embed.set_thumbnail(url="attachment://item.png")
        
        requisicao_id = str(message.id)
        bot.requisicoes_pendentes[requisicao_id] = {
            "user_id": message.author.id,
            "itens": itens_faltando
        }
        
        canal_requisicoes = bot.get_channel(1331515800607002675)
        
        if canal_requisicoes:
            view = RequisicaoView(requisicao_id)
            await canal_requisicoes.send(
                embed=embed,
                file=file,
                view=view
            )
            await message.channel.send("✅ Sua requisição foi enviada para os administradores!")
        else:
            await message.channel.send("❌ Erro ao processar sua requisição. Canal não configurado.")
    
    except Exception as e:
        print(f"Erro ao processar requisição: {e}")
        await message.channel.send("❌ Ocorreu um erro ao processar sua imagem. Tente novamente.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    
    if message.author == bot.user:
        return
    
    if isinstance(message.channel, discord.DMChannel) and message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                await processar_requisicao(message, attachment)

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

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
bot.run(os.getenv("DISCORD_TOKEN"))
