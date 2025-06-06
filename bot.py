import os
import discord
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
intents.message_content = True  # Habilita leitura de mensagens
bot = commands.Bot(command_prefix="/", intents=intents)

acertos_arquivo = "acertos.txt"

class AcertoView(discord.ui.View):
    @discord.ui.button(label="Responder", style=discord.ButtonStyle.primary)
    async def responder(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message("Verifique sua DM para responder!", ephemeral=True)
            await interaction.user.send("Quantos de acerto você tem? (ex: 450)")

            def check(m):
                return m.author.id == interaction.user.id and isinstance(m.channel, discord.DMChannel)

            msg = await bot.wait_for("message", check=check, timeout=60)

            # Atualiza ou adiciona acerto
            try:
                with open(acertos_arquivo, "r", encoding="utf-8") as f:
                    linhas = f.readlines()
            except FileNotFoundError:
                linhas = []

            usuario = interaction.user.name
            novo_valor = msg.content.strip()
            encontrado = False
            novas_linhas = []

            for linha in linhas:
                if linha.startswith(f"{usuario} ="):
                    novas_linhas.append(f"{usuario} = {novo_valor}\n")
                    encontrado = True
                else:
                    novas_linhas.append(linha)

            if not encontrado:
                novas_linhas.append(f"{usuario} = {novo_valor}\n")

            with open(acertos_arquivo, "w", encoding="utf-8") as f:
                f.writelines(novas_linhas)

            await interaction.user.send("✅ Sua resposta foi registrada com sucesso!")
        except asyncio.TimeoutError:
            await interaction.user.send("⏰ Tempo esgotado! Por favor, clique no botão novamente.")

@bot.command()
@commands.has_permissions(administrator=True)
async def pesquisa(ctx):
    await ctx.message.delete(delay=5)
    view = AcertoView()
    await ctx.send("📊 **Quantos de acerto você tem?**", view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def rankacerto(ctx):
    try:
        with open(acertos_arquivo, "r", encoding="utf-8") as f:
            dados = [linha.strip().split(" = ") for linha in f if " = " in linha]
            dados = sorted(dados, key=lambda x: int(x[1]), reverse=True)
    except FileNotFoundError:
        await ctx.send("Nenhum dado de acertos encontrado.")
        return

    if not dados:
        await ctx.send("Nenhum dado registrado ainda.")
        return

    resposta = "**🏆 Ranking de Acertos:**\n"
    for i, (usuario, acerto) in enumerate(dados, start=1):
        status = "✅(530+)" if int(acerto) >= 530 else "❌(530+)"
        resposta += f"{i}. {usuario} — {acerto} acerto(s) {status}\n"

    await ctx.send(resposta)

bot.run(os.environ["DISCORD_TOKEN"])
