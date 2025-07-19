import asyncio
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ChannelPostHandler, ContextTypes, filters
)

# === CONFIGURATION ===
TOKEN = "7334376683:AAGbw9r-3YQ8lwEur1bSe0GkA9tCYABkmIM"
DATA_FILE = "data.json"

# === BASE DE DONNÉES ===
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"admins": [5116530698], "groups": {}, "users": []}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# === COMMANDES DE BASE ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)

    keyboard = [[InlineKeyboardButton("Rejoindre le canal", url="https://t.me/sineur_x_bot")]]
    texte = (
        "Bienvenue !\nCe bot supprime automatiquement les messages dans les groupes et canaux.\n\n"
        "Commandes :\n"
        "/on - Activer l’auto-suppression\n"
        "/off - Désactiver l’auto-suppression\n"
        "/setdelay [secondes] - Définir le délai de suppression"
    )
    await update.message.reply_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    data = load_data()
    data["groups"].setdefault(chat_id, {})["enabled"] = True
    save_data(data)
    await update.message.reply_text("✅ Auto-suppression activée.")

async def cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    data = load_data()
    data["groups"].setdefault(chat_id, {})["enabled"] = False
    save_data(data)
    await update.message.reply_text("❌ Auto-suppression désactivée.")

async def cmd_setdelay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    data = load_data()
    try:
        delay = int(context.args[0])
        data["groups"].setdefault(chat_id, {})["delay"] = delay
        save_data(data)
        await update.message.reply_text(f"⏱️ Délai de suppression défini à {delay} secondes.")
    except:
        await update.message.reply_text("❗ Utilisation : /setdelay 10")

# === GESTION DES GROUPES ===
async def auto_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = str(update.effective_chat.id)
    data = load_data()

    if chat_id not in data["groups"]:
        data["groups"][chat_id] = {"enabled": False, "delay": 3}
        save_data(data)

    conf = data["groups"].get(chat_id, {})
    if conf.get("enabled", False):
        delay = conf.get("delay", 3)
        await asyncio.sleep(delay)
        try:
            await update.message.delete()
        except Exception as e:
            print(f"[GROUPE] Erreur suppression : {e}")

# === GESTION DES CANAUX ===
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    chat_id = str(post.chat_id)
    text = post.text or ""
    data = load_data()

    if chat_id not in data["groups"]:
        data["groups"][chat_id] = {"enabled": False, "delay": 3}
        save_data(data)

    if text == "/on":
        data["groups"][chat_id]["enabled"] = True
        save_data(data)
        await context.bot.send_message(chat_id, "✅ Auto-suppression activée.")
        return

    if text.startswith("/setdelay"):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            delay = int(parts[1])
            data["groups"][chat_id]["delay"] = delay
            data["groups"][chat_id]["enabled"] = True
            save_data(data)
            await context.bot.send_message(chat_id, f"⏱️ Délai de suppression défini à {delay} secondes.")
            return

    conf = data["groups"].get(chat_id, {})
    if conf.get("enabled", False):
        delay = conf.get("delay", 3)
        await asyncio.sleep(delay)
        try:
            await context.bot.delete_message(chat_id, post.message_id)
        except Exception as e:
            print(f"[CANAL] Erreur suppression : {e}")

# === ADMINISTRATION ===
def is_admin(user_id):
    return user_id == 5116530698

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        username = context.args[0].lstrip('@')
        user = await context.bot.get_chat(username)
        data = load_data()
        if user.id not in data["admins"]:
            data["admins"].append(user.id)
            save_data(data)
            await update.message.reply_text(f"✅ @{username} ajouté aux admins.")
    except:
        await update.message.reply_text("⚠️ Utilisation : /addadmin @username")

async def ban_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        username = context.args[0].lstrip('@')
        user = await context.bot.get_chat(username)
        data = load_data()
        if user.id in data["admins"]:
            data["admins"].remove(user.id)
            save_data(data)
            await update.message.reply_text(f"❌ @{username} retiré des admins.")
    except:
        await update.message.reply_text("⚠️ Utilisation : /banadmin @username")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    txt = "👮 Admins :\n" + "\n".join([str(a) for a in data["admins"]])
    await update.message.reply_text(txt)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    msg = " ".join(context.args)
    data = load_data()
    count = 0
    for user_id in data["users"]:
        try:
            await context.bot.send_message(user_id, msg)
            count += 1
        except:
            pass
    await update.message.reply_text(f"📤 Message envoyé à {count} utilisateurs.")

async def broadcast_pub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    msg = " ".join(context.args)
    data = load_data()
    count = 0
    for chat_id in data["groups"]:
        try:
            await context.bot.send_message(chat_id, msg)
            count += 1
        except:
            pass
    await update.message.reply_text(f"📣 Message envoyé dans {count} groupes/canaux.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    await update.message.reply_text(
        f"📊 Stats :\n"
        f"👥 Utilisateurs : {len(data['users'])}\n"
        f"📢 Groupes/Canaux : {len(data['groups'])}\n"
        f"👮 Admins : {len(data['admins'])}"
    )

# === LANCEMENT DU BOT ===
app = ApplicationBuilder().token(TOKEN).build()

# Commandes utilisateur
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("on", cmd_on))
app.add_handler(CommandHandler("off", cmd_off))
app.add_handler(CommandHandler("setdelay", cmd_setdelay))

# Admin
app.add_handler(CommandHandler("addadmin", add_admin))
app.add_handler(CommandHandler("banadmin", ban_admin))
app.add_handler(CommandHandler("admins", list_admins))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("broadcast_pub", broadcast_pub))
app.add_handler(CommandHandler("stats", stats))

# Message dans groupe
app.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, auto_delete))

# Message dans canal
app.add_handler(ChannelPostHandler(handle_channel_post))

print("🚀 Bot lancé...")
app.run_polling(drop_pending_updates=True, allowed_updates=["message", "channel_post"])