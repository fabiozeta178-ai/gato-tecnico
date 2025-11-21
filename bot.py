import discord
from discord import app_commands, SyncWebhook, Embed
from discord.ext import commands, tasks
import json
import os
import sys

# ---------- CONFIG ----------
with open("config.json") as f:
    cfg = json.load(f)

ALLOWED_USERS = cfg.get("allowed_users", [])

# ---------- BOT SETUP ----------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- STATO BOT ----------
@tasks.loop(minutes=1)
async def update_status():
    total_members = sum(guild.member_count for guild in bot.guilds)
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name=f"miagolando a {total_members} membri"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)

# ---------- DINAMIC COMMAND LOADER ----------
def load_dynamic():
    cmds = os.listdir("commands")
    for c in cmds:
        if c.endswith(".txt") and c.lower() != "readme.txt":
            name = c.replace(".txt", "")
            if name in [cmd.name for cmd in bot.tree.get_commands()]:
                continue

            async def _cmd(interaction: discord.Interaction, cmd_name: str = name):
                file_path = f"commands/{cmd_name}.txt"
                if not os.path.exists(file_path):
                    return await interaction.response.send_message("Comando non trovato!", ephemeral=True)

                with open(file_path) as f:
                    try:
                        data = json.load(f)

                        # ---------- WEBHOOK HANDLER (VERSIONE FIXATA) ----------
                        if "webhook_url" in data:
                            webhook = SyncWebhook.from_url(data["webhook_url"])

                            raw_color = data.get("color", "#00FF00")

                            # SAFE COLOR PARSER — accetta HEX e DECIMAL
                            try:
                                if isinstance(raw_color, str) and raw_color.startswith("#"):
                                    color = int(raw_color.replace("#", ""), 16)
                                else:
                                    color = int(raw_color)
                            except:
                                color = 0x00FF00

                            embed = Embed(
                                title=data.get("title", ""),
                                description=data.get("description", ""),
                                color=color
                            )

                            if data.get("thumbnail"):
                                embed.set_thumbnail(url=data["thumbnail"])

                            # INVIO WEBHOOK
                            try:
                                webhook.send(embeds=[embed])
                            except Exception as e:
                                return await interaction.response.send_message(
                                    f"Errore durante l'invio del webhook:\n```{e}```",
                                    ephemeral=True
                                )

                            channel = bot.get_channel(data["channel_id"])
                            return await interaction.response.send_message(
                                f"Embed `{cmd_name}` inviato in {channel.mention}!",
                                ephemeral=True
                            )

                        # ---------- SE NON È WEBHOOK, INVIA TESTO ----------
                        else:
                            await interaction.response.send_message(data, ephemeral=True)

                    except Exception:
                        # Se il file NON è JSON, invia il contenuto puro
                        f.seek(0)
                        await interaction.response.send_message(f.read(), ephemeral=True)

            bot.tree.add_command(app_commands.Command(
                name=name,
                description=f"Comando dinamico {name}",
                callback=_cmd
            ))

# ---------- CREATE TEXT COMMAND ----------
async def createcmd(interaction: discord.Interaction, name: str, content: str):
    if interaction.user.id not in ALLOWED_USERS:
        return await interaction.response.send_message("Non hai il permesso!", ephemeral=True)
    file_path = f"commands/{name}.txt"
    if os.path.exists(file_path):
        return await interaction.response.send_message(f"Il comando `{name}` esiste già!", ephemeral=True)
    with open(file_path, "w") as f:
        f.write(content)
    load_dynamic()
    await interaction.response.send_message(f"Comando `{name}` creato!", ephemeral=True)

# ---------- CREATE WEBHOOK COMMAND ----------
async def createwebhookcmd(
    interaction: discord.Interaction,
    name: str,
    webhook_url: str,
    title: str,
    description: str,
    channel: discord.TextChannel,
    color: str = "#00FF00",
    thumbnail: str = None
):
    if interaction.user.id not in ALLOWED_USERS:
        return await interaction.response.send_message("Non hai il permesso!", ephemeral=True)

    file_path = f"commands/{name}.txt"
    if os.path.exists(file_path):
        return await interaction.response.send_message(f"Il comando `{name}` esiste già!", ephemeral=True)

    json_data = {
        "webhook_url": webhook_url,
        "title": title,
        "description": description,
        "channel_id": channel.id,
        "color": color,
        "thumbnail": thumbnail
    }

    with open(file_path, "w") as f:
        json.dump(json_data, f)

    load_dynamic()
    await interaction.response.send_message(
        f"Comando webhook `{name}` creato e collegato a {channel.mention}!",
        ephemeral=True
    )

# ---------- DELETE ----------
async def deletecmd(interaction: discord.Interaction, name: str):
    if interaction.user.id not in ALLOWED_USERS:
        return await interaction.response.send_message("Non hai il permesso!", ephemeral=True)
    file_path = f"commands/{name}.txt"
    if not os.path.exists(file_path):
        return await interaction.response.send_message("Comando non trovato!", ephemeral=True)
    os.remove(file_path)
    await interaction.response.send_message(f"Comando `{name}` eliminato!", ephemeral=True)

# ---------- SHUTDOWN ----------
async def shutdown(interaction: discord.Interaction):
    if interaction.user.id not in ALLOWED_USERS:
        return await interaction.response.send_message("Non hai il permesso!", ephemeral=True)
    await interaction.response.send_message("Shutdown...", ephemeral=True)
    await bot.close()

# ---------- RESTART ----------
async def restart(interaction: discord.Interaction):
    if interaction.user.id not in ALLOWED_USERS:
        return await interaction.response.send_message("Non hai il permesso!", ephemeral=True)
    await interaction.response.send_message("Riavvio...", ephemeral=True)
    python = sys.executable
    os.execl(python, python, *sys.argv)

# ---------- ON READY ----------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    update_status.start()

    # Registrazione comandi statici
    bot.tree.add_command(app_commands.Command(name="createcmd", description="Crea un comando testuale", callback=createcmd))
    bot.tree.add_command(app_commands.Command(name="createwebhookcmd", description="Crea un comando webhook", callback=createwebhookcmd))
    bot.tree.add_command(app_commands.Command(name="deletecmd", description="Elimina un comando", callback=deletecmd))
    bot.tree.add_command(app_commands.Command(name="shutdown", description="Spegne il bot", callback=shutdown))
    bot.tree.add_command(app_commands.Command(name="restart", description="Riavvia il bot", callback=restart))

    # Carica comandi dinamici
    load_dynamic()

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(e)

from keep_alive import keep_alive
keep_alive()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable not set!")
    print("Please add your Discord bot token to the Secrets.")
    sys.exit(1)

bot.run(TOKEN)