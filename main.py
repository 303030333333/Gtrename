import asyncio
import json
import os
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

nest_asyncio.apply()

TOKEN = "7334376683:AAGbw9r-3YQ8lwEur1bSe0GkA9tCYABkmIM"  # Remplace ici avec ton vrai token
DATA_FILE = "data.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"admins": [5116530698], "groups": {}, "users": []}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def keep_alive():
    while True:
        data = load_data()
        for chat_id in data["groups"]:
            data["groups"][chat_id]["enabled"] = True
        save_data(data)
        print("[AUTO] Vérif auto-suppression.")
        await asyncio.sleep(1800)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)

    keyboard = [[InlineKeyboardButton("🔗 Canal", url="https://t.me/sineur_x_bot")]]
    await update.message.reply_text(
        "Bienvenue ! Bot actif.\n\n"
        "/on - Activer suppression\n"
        "/off - Désactiver\n"
        "/setdelay 10 - Délai suppression\n"
        "/admins - Voir admins",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    data = load_data()
    data["groups"].setdefault(chat_id, {"enabled": True, "delay": 3})["enabled"] = True
    save_data(data)
    await update.message.reply_text("✅ Suppression activée.")

async def cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    data = load_data()
    data["groups"].setdefault(chat_id, {})["enabled"] = False
    save_data(data)
    await update.message.reply_text("❌ Suppression désactivée.")

async def cmd_setdelay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    try:
        delay = int(context.args[0])
        data = load_data()
        data["groups"].setdefault(chat_id, {})["delay"] = delay
        save_data(data)
        await update.message.reply_text(f"⏱ Délai défini à {delay} sec.")
    except:
        await update.message.reply_text("Utilisation : /setdelay 10")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if user_id in data["admins"]:
        try:
            new_id = int(context.args[0])
            if new_id not in data["admins"]:
                data["admins"].append(new_id)
                save_data(data)
                await update.message.reply_text(f"✅ Admin ajouté : {new_id}")
        except:
            await update.message.reply_text("Utilisation : /addadmin <id>")

async def ban_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if user_id in data["admins"]:
        try:
            ban_id = int(context.args[0])
            if ban_id in data["admins"]:
                data["admins"].remove(ban_id)
                save_data(data)
                await update.message.reply_text(f"❌ Admin retiré : {ban_id}")
        except:
            await update.message.reply_text("Utilisation : /banadmin <id>")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    text = "👑 Admins :\n" + "\n".join([str(a) for a in data["admins"]])
    await update.message.reply_text(text)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if user_id not in data["admins"]:
        return
    msg = " ".join(context.args)
    for uid in data["users"]:
        try:
            await context.bot.send_message(chat_id=uid, text=msg)
        except:
            pass
    await update.message.reply_text("📣 Message envoyé.")

async def broadcast_pub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if user_id not in data["admins"]:
        return
    msg = " ".join(context.args)
    for gid in data["groups"]:
        try:
            await context.bot.send_message(chat_id=gid, text=msg)
        except:
            pass
    await update.message.reply_text("📢 Envoyé dans les groupes.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    await update.message.reply_text(
        f"👥 Users : {len(data['users'])}\n📣 Canaux : {len(data['groups'])}"
    )

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.channel_post.chat_id)
    message_id = update.channel_post.message_id
    data = load_data()

    if chat_id not in data["groups"]:
        data["groups"][chat_id] = {"enabled": False, "delay": 3}
        save_data(data)

    config = data["groups"].get(chat_id, {})
    if config.get("enabled", False):
        delay = config.get("delay", 3)
        await asyncio.sleep(delay)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            print("[SUPPR] Message supprimé.")
        except Exception as e:
            print("Erreur suppression :", e)

app = ApplicationBuilder().token(TOKEN).build()

# Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("on", cmd_on))
app.add_handler(CommandHandler("off", cmd_off))
app.add_handler(CommandHandler("setdelay", cmd_setdelay))
app.add_handler(CommandHandler("addadmin", add_admin))
app.add_handler(CommandHandler("banadmin", ban_admin))
app.add_handler(CommandHandler("admins", list_admins))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("broadcast_pub", broadcast_pub))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, handle_channel_post))

print("✅ Bot lancé...")

async def main():
    asyncio.create_task(keep_alive())
    await app.run_polling(allowed_updates=["message", "channel_post"])

try:
    asyncio.run(main())
except Exception as e:
    print("Erreur :", e)