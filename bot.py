import discord, json, time, os
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("TOKEN")
GEN_ROLE_NAME = "Generator"
LOG_CHANNEL_ID = 1234567890123
COOLDOWN_SECONDS = 60

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

cooldowns = {}

# ---------- STOCK ----------
def load_stock():
    with open("stock.json", "r") as f:
        return json.load(f)

def save_stock(data):
    with open("stock.json", "w") as f:
        json.dump(data, f, indent=4)

# ---------- READY ----------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Online as {bot.user}")

# ---------- /gen ----------
@bot.tree.command(name="gen", description="Generate an item")
@app_commands.describe(service="Service name")
async def gen(interaction: discord.Interaction, service: str):
    stock = load_stock()
    user_id = interaction.user.id
    now = time.time()

    # role check
    role = discord.utils.get(interaction.guild.roles, name=GEN_ROLE_NAME)
    if role not in interaction.user.roles:
        await interaction.response.send_message("❌ Missing role.", ephemeral=True)
        return

    # cooldown
    if user_id in cooldowns and now - cooldowns[user_id] < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - (now - cooldowns[user_id]))
        await interaction.response.send_message(
            f"⏳ Cooldown: {remaining}s", ephemeral=True
        )
        return

    service = service.lower()
    if service not in stock or not stock[service]:
        await interaction.response.send_message("❌ Out of stock.", ephemeral=True)
        return

    item = stock[service].pop(0)
    save_stock(stock)
    cooldowns[user_id] = now

    # DM item
    await interaction.user.send(
        f"✅ **{service} generated:**\n```{item}```"
    )
    await interaction.response.send_message(
        "📩 Sent to your DMs.", ephemeral=True
    )

    # log
    log = bot.get_channel(LOG_CHANNEL_ID)
    if log:
        await log.send(
            f"📤 **GEN** | {interaction.user} | {service}"
        )

# ---------- /stock ----------
@bot.tree.command(name="stock", description="Check stock")
async def stock_cmd(interaction: discord.Interaction):
    stock = load_stock()
    msg = "\n".join(f"**{k}**: {len(v)}" for k, v in stock.items())
    await interaction.response.send_message(msg, ephemeral=True)

# ---------- /restock ----------
@bot.tree.command(name="restock", description="Restock items (admin)")
@app_commands.describe(service="Service", items="item1 | item2 | item3")
async def restock(interaction: discord.Interaction, service: str, items: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return

    stock = load_stock()
    service = service.lower()
    new_items = [i.strip() for i in items.split("|") if i.strip()]

    stock.setdefault(service, []).extend(new_items)
    save_stock(stock)

    await interaction.response.send_message(
        f"✅ Added `{len(new_items)}` items to **{service}**.", ephemeral=True
    )

bot.run(TOKEN)

