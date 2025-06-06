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
bot = commands.Bot(command_prefix="!", intents=intents)  # Corrigido: intents em vez de intents
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
            try:
                acertos = int(msg.content.strip())
            except ValueError:
                await msg.channel.send("❌ Por favor, envie apenas números (ex: 450)")
                return

            nome_usuario = interaction.user.name

            novos_dados = []
            atualizado = False

            if os.path.exists(acertos_arquivo):
                with open(acertos_arquivo, "r") as f:
                    for linha in f:
                        if " = " in linha:  # Verificação adicional para evitar erros
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

@bot.tree.command(name="requisicao", description="Solicitar envio de itens faltantes")
async def requisicao(interaction: discord.Interaction):
    """Comando principal que inicia o processo de requisição"""
    try:
        await interaction.user.send("📸 Por favor, envie a imagem dos itens faltantes aqui nesta conversa privada.")
        await interaction.response.send_message(
            "📩 Verifique sua DM (mensagens privadas) para enviar a imagem!",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Não consegui enviar DM para você. Verifique suas configurações de privacidade.",
            ephemeral=True
        )

@bot.event
async def on_message(message):
    # Processar comandos primeiro
    await bot.process_commands(message)
    
    # Só processar se for mensagem privada e não for do bot
    if message.author == bot.user or not isinstance(message.channel, discord.DMChannel):
        return
    
    # Verificar se tem anexo de imagem
    if not message.attachments or not message.attachments[0].filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        await message.channel.send("❌ Por favor, envie uma imagem (PNG, JPG ou JPEG).")
        return

    # Aqui você pode processar a imagem ou enviar para um canal de administradores
    # Vou criar um exemplo enviando para um canal específico
    
    # Substitua CHANNEL_ID pelo ID do canal onde as requisições devem ser enviadas
    channel_id = 1380521025804177448  # Troque pelo ID real do seu canal
    channel = bot.get_channel(channel_id)
    
    if channel:
        embed = discord.Embed(
            title=f"Requisição de {message.author.display_name}",
            description=f"📋 Itens solicitados\n\n"
                       f"🔹 **Verificação manual necessária**\n"
                       f"Administradores, verifiquem a imagem e aprovem se válida.",
            color=discord.Color.orange()
        )
        embed.set_image(url=message.attachments[0].url)
        
        class ApproveView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
            @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, custom_id="approve_req")
            async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Apenas administradores podem aprovar.", ephemeral=True)
                    return
                    
                embed = interaction.message.embeds[0]
                embed.color = discord.Color.green()
                embed.description = "✅ **Requisição Aprovada**\n\nOs itens serão enviados em breve."
                
                await interaction.message.edit(embed=embed, view=None)
                
                try:
                    await message.author.send(
                        f"✅ Sua requisição foi aprovada por {interaction.user.mention}!\n"
                        f"Os itens serão enviados em breve."
                    )
                except discord.Forbidden:
                    pass
                    
                await interaction.response.send_message("Requisição aprovada com sucesso!", ephemeral=True)
            
            @discord.ui.button(label="Recusar", style=discord.ButtonStyle.danger, custom_id="reject_req")
            async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ Apenas administradores podem recusar.", ephemeral=True)
                    return
                    
                embed = interaction.message.embeds[0]
                embed.color = discord.Color.red()
                embed.description = "❌ **Requisição Recusada**\n\nVerifique os requisitos e tente novamente."
                
                await interaction.message.edit(embed=embed, view=None)
                
                try:
                    await message.author.send(
                        f"❌ Sua requisição foi recusada por {interaction.user.mention}.\n"
                        f"Motivo: Verificação manual não aprovada."
                    )
                except discord.Forbidden:
                    pass
                    
                await interaction.response.send_message("Requisição recusada com sucesso!", ephemeral=True)

        await channel.send(embed=embed, view=ApproveView())
        await message.channel.send("✅ Sua requisição foi enviada para os administradores! Aguarde a aprovação.")
    else:
        await message.channel.send("❌ O canal de requisições não foi configurado corretamente.")
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
    await asyncio.sleep(3000)  # Considerar reduzir este tempo
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
        dados = []
        for linha in f:
            if " = " in linha.strip():
                dados.append(linha.strip().split(" = "))
    
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
    
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
bot.run(os.getenv("DISCORD_TOKEN"))
