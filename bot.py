import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime

TOKEN = "SEU_TOKEN_AQUI"

# IDs dos canais
CANAL_PUBLICO_ID = 123456789012345678   # canal onde aparece o embed com botão
CANAL_LOG_ID = 987654321098765432       # canal de logs/admins

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class CheckInView(discord.ui.View):
    def __init__(self, boss, log_channel):
        super().__init__(timeout=300)  # 5 minutos
        self.boss = boss
        self.log_channel = log_channel

    @discord.ui.button(label="✅ Check-in", style=discord.ButtonStyle.green)
    async def check_in_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.log_channel.send(
            f"📌 {interaction.user.mention} fez check-in para **{self.boss}**"
        )
        await interaction.response.send_message(
            f"Você registrou presença para **{self.boss}**!", ephemeral=True
        )

    async def on_timeout(self):
        await self.log_channel.send(f"⏳ Check-in para **{self.boss}** encerrado!")


@bot.event
async def on_ready():
    print(f"Bot logado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")


@bot.tree.command(name="check-in", description="Inicia um check-in para Boss (somente admins).")
@app_commands.describe(
    boss="Nome do Boss",
    imagem_boss="URL da imagem do Boss",
    mapa="URL da imagem da localização do Boss"
)
async def check_in(interaction: discord.Interaction, boss: str, imagem_boss: str, mapa: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
        return

    guild = interaction.guild
    canal_publico = guild.get_channel(CANAL_PUBLICO_ID)
    canal_log = guild.get_channel(CANAL_LOG_ID)

    embed = discord.Embed(
        title=f"📢 Check-in aberto para {boss}!",
        description="Clique no botão abaixo para confirmar sua presença.",
        color=discord.Color.green()
    )
    embed.set_image(url=imagem_boss)
    embed.add_field(name="📍 Localização", value="Veja o mapa abaixo", inline=False)

    # segunda imagem (mapa) como thumbnail ou anexo no mesmo embed
    embed.set_thumbnail(url=mapa)

    view = CheckInView(boss, canal_log)
    await canal_publico.send(embed=embed, view=view)

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    await canal_log.send(
        f"✅ Check-in para **{boss}** aberto por {interaction.user.mention} em {agora}"
    )

    await interaction.response.send_message(
        f"Check-in para **{boss}** aberto em {canal_publico.mention}!", ephemeral=True
    )


bot.run(TOKEN)
