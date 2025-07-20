import logging
import os
import uuid
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.filters import Command
from aiogram.types import Message
import yt_dlp
from telegraph import Telegraph
from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
# -------------------------------
# Configuration
# -------------------------------
BOT_TOKEN = "7771993655:AAEsuPrx3vn34Ql4ws_k6pPXj91X1uecaAM"  # Remplace par ton token BotFather
ADMIN_IDS = [5116530698]  # Remplace par tes IDs admin
FORCE_SUB_CHANNELS = []  # Pas d'abonnement forcé
WELCOME_IMAGE_URL = "https://telegra.ph/file/4a7f3e3f9b8c5d6e7f8g9.jpg"  # URL de ton image de bienvenue

# Configuration MongoDB (temporairement désactivée)
MONGODB_URI = None  # À remplacer par une URI MongoDB valide
DATABASE_NAME = "altoftoure"  # Nom de ta base de données

# Configuration API Telegram (pour pyrogram si nécessaire)
API_ID = 24777493  # Remplace par ton API ID depuis my.telegram.org
API_HASH = "bf5a6381d07f045af4faeb46d7de36e5"  # Remplace par ton API Hash depuis my.telegram.org

# -------------------------------
# Initialisation du bot et MongoDB
# -------------------------------
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=MemoryStorage())

# Initialisation MongoDB (temporairement désactivée)
if MONGODB_URI:
    mongo_client = AsyncIOMotorClient(MONGODB_URI)
    db = mongo_client[DATABASE_NAME]
    # Collections MongoDB
    users_collection = db.users
    downloads_collection = db.downloads
    admin_logs_collection = db.admin_logs
else:
    mongo_client = None
    db = None
    users_collection = None
    downloads_collection = None
    admin_logs_collection = None

# Fonction de vérification d’abonnement
async def check_subscription(user_id: int, bot) -> bool:
    """
    Vérifie si l'utilisateur est abonné à toutes les chaînes obligatoires.
    Renvoie True si l'utilisateur est abonné à toutes, sinon False.
    Envoie un message avec les boutons si l'utilisateur n'est pas abonné.
    """
    not_subscribed = []

    for channel in FORCE_SUB_CHANNELS:
        try:
            # Utiliser directement l'ID du channel au lieu de get_chat
            member = await bot.get_chat_member(f"@{channel}", user_id)

            if member.status in [
                ChatMemberStatus.LEFT,
                ChatMemberStatus.KICKED,
                ChatMemberStatus.BANNED
            ]:
                not_subscribed.append(channel)

        except Exception as e:
            print(f"Erreur lors de la vérification pour @{channel} :", e)
            # Considérer que l'utilisateur n'est pas abonné en cas d'erreur
            not_subscribed.append(channel)

    if not_subscribed:
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=f"🔔 Rejoindre @{chan}", url=f"https://t.me/{chan}")]
                for chan in not_subscribed
            ] + [
                [types.InlineKeyboardButton(text="✅ J’ai rejoint", callback_data="check_sub")]
            ]
        )
        await bot.send_message(
            user_id,
            "🚫 Pour utiliser ce bot, tu dois d’abord rejoindre ces chaînes 👇",
            reply_markup=keyboard
        )
        return False

    return True

def download_video(url: str) -> str:
    """
    Télécharge une vidéo YouTube et renvoie le chemin du fichier téléchargé.
    """
    output_filename = f"{uuid.uuid4()}.mp4"
    
    # Liste de User-Agents pour rotation
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
    ]
    
    # Configuration améliorée pour yt-dlp avec rotation d'User-Agent
    ydl_opts = {
        'format': 'best[height<=720][filesize<45M]/best[height<=480][filesize<45M]/best[height<=360][filesize<45M]/worst[filesize<50M]/worst',
        'outtmpl': output_filename,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': False,
        'extractor_retries': 3,
        'socket_timeout': 60,
        'http_chunk_size': 10485760,
        'retries': 3,
        'extract_flat': False,
        'writethumbnail': False,
        'writeinfojson': False,
        # Rotation d'User-Agent
        'http_headers': {
            'User-Agent': user_agents[hash(url) % len(user_agents)],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Encoding': 'gzip,deflate',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            'Keep-Alive': '115',
            'Connection': 'keep-alive',
        },
        # Options supplémentaires pour contourner les restrictions
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        # Éviter la détection de bot
        'sleep_interval': 1,
        'max_sleep_interval': 5,
    }

    try:
        print(f"Téléchargement de: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Vérifier si le fichier existe et n'est pas vide
        if os.path.exists(output_filename) and os.path.getsize(output_filename) > 1024:
            print(f"Téléchargement réussi: {output_filename}")
            return output_filename
        else:
            print("Fichier téléchargé invalide")
            if os.path.exists(output_filename):
                os.remove(output_filename)
            return None

    except Exception as e:
        print(f"Erreur de téléchargement: {e}")
        if os.path.exists(output_filename):
            try:
                os.remove(output_filename)
            except:
                pass
        return None

def upload_image_to_telegraph(file_path: str) -> str:
    """
    Upload une image sur Telegraph et renvoie l'URL.
    """
    telegraph = Telegraph()
    telegraph.create_account(short_name="bot")
    try:
        with open(file_path, 'rb') as f:
            response = telegraph.upload_file(f)
        if isinstance(response, list) and len(response) > 0:
            return "https://telegra.ph" + response[0]['src']
        else:
            return None
    except Exception as e:
        print("Erreur lors de l'upload sur Telegraph:", e)
        return None

def is_admin(user_id: int) -> bool:
    """
    Vérifie si l'utilisateur est dans la liste des admins.
    """
    return user_id in ADMIN_IDS

# -------------------------------
# Fonctions MongoDB
# -------------------------------
async def save_user(user_id: int, username: str = None, first_name: str = None):
    """Sauvegarder les informations utilisateur dans MongoDB"""
    if not users_collection:
        return  # MongoDB non configuré
    user_data = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "joined_date": datetime.now(),
        "last_activity": datetime.now(),
        "is_banned": False,
        "download_count": 0
    }
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": user_data},
        upsert=True
    )

async def log_download(user_id: int, url: str, success: bool = True, error_msg: str = None):
    """Enregistrer un téléchargement dans MongoDB"""
    if not downloads_collection:
        return  # MongoDB non configuré
    download_data = {
        "user_id": user_id,
        "url": url,
        "timestamp": datetime.now(),
        "success": success,
        "error_message": error_msg
    }
    await downloads_collection.insert_one(download_data)

    # Incrémenter le compteur de téléchargements de l'utilisateur
    if success and users_collection:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"download_count": 1}}
        )

async def get_user_stats(user_id: int = None):
    """Obtenir les statistiques des utilisateurs"""
    if not users_collection:
        # Retourner des stats en mémoire si MongoDB n'est pas configuré
        return {
            "total_users": len(subscribers) if 'subscribers' in globals() else 0,
            "total_downloads": 0,
            "banned_users": len(banned_users) if 'banned_users' in globals() else 0
        }
    
    if user_id:
        user = await users_collection.find_one({"user_id": user_id})
        downloads = await downloads_collection.count_documents({"user_id": user_id})
        return {"user": user, "downloads": downloads}
    else:
        total_users = await users_collection.count_documents({})
        total_downloads = await downloads_collection.count_documents({})
        banned_users_count = await users_collection.count_documents({"is_banned": True})
        return {
            "total_users": total_users,
            "total_downloads": total_downloads,
            "banned_users": banned_users_count
        }

async def ban_user_db(user_id: int, banned_by: int):
    """Bannir un utilisateur dans MongoDB"""
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"is_banned": True, "banned_date": datetime.now(), "banned_by": banned_by}}
    )

async def unban_user_db(user_id: int, unbanned_by: int):
    """Débannir un utilisateur dans MongoDB"""
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"is_banned": False, "unbanned_date": datetime.now(), "unbanned_by": unbanned_by}}
    )

async def is_user_banned(user_id: int) -> bool:
    """Vérifier si un utilisateur est banni"""
    if not users_collection:
        return user_id in banned_users  # Utiliser la liste en mémoire
    user = await users_collection.find_one({"user_id": user_id})
    return user.get("is_banned", False) if user else False

# -------------------------------
# Handlers du bot
# -------------------------------

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    # Vérifier si l'utilisateur est banni
    if await is_user_banned(user_id):
        await message.reply("❌ Vous êtes banni de ce bot.")
        return

    await save_user(user_id, username, first_name)
    
    # Initialize subscribers if it doesn't exist
    global subscribers
    if 'subscribers' not in globals():
        subscribers = set()
    subscribers.add(user_id)

    # Création du clavier inline
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="📥 Télécharger une vidéo", callback_data="download_video")
            ],
            [
                types.InlineKeyboardButton(text="📢 Rejoindre notre canal", url="https://t.me/sineur_x_bot")
            ]
        ]
    )
    
    # Message de bienvenue avec image
    welcome_text = ("🎬 **Bienvenue sur notre bot de téléchargement YouTube !** 📱\n\n"
                   "Ce bot vous permet de télécharger facilement des vidéos depuis YouTube.\n\n"
                   "✅ Téléchargement rapide\n"
                   "✅ Haute qualité\n"
                   "✅ Simple à utiliser\n\n"
                   "📌 **Comment utiliser :**\n"
                   "1. Cliquez sur 'Télécharger une vidéo'\n"
                   "2. Ou envoyez directement votre lien YouTube\n\n"
                   "Choisissez une option ci-dessous pour commencer :")
    
    # Essayer d'envoyer avec l'image
    try:
        # Utiliser une image YouTube fonctionnelle
        await bot.send_photo(
            chat_id=message.chat.id,
            photo="https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/YouTube_full-color_icon_%282017%29.svg/2560px-YouTube_full-color_icon_%282017%29.svg.png",
            caption=welcome_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Erreur avec l'image: {e}")
        # Envoyer sans image en cas d'erreur
        await message.answer(
            welcome_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data == "download_video")
async def process_download_video(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await bot.send_message(callback_query.from_user.id, "Envoie-moi le lien YouTube à télécharger.")

@dp.callback_query(lambda c: c.data == "admin_panel")
async def process_admin_panel(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer(text="Accès refusé. Vous n'êtes pas administrateur.")
        return

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
                types.InlineKeyboardButton(text="👮‍♂️ Add Admin", callback_data="admin_addadmin")
            ],
            [
                types.InlineKeyboardButton(text="🚫 Ban Admin", callback_data="admin_banadmin"),
                types.InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")
            ],
            [
                types.InlineKeyboardButton(text="🧹 Vide Cache", callback_data="admin_videcache"),
                types.InlineKeyboardButton(text="📁 Voir Stockage", callback_data="admin_storage")
            ]
        ]
    )

    await bot.send_message(
        callback_query.from_user.id, 
        "🛠 **Panneau Admin:**\n\nChoisissez une action :", 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback_query.answer()

@dp.message(lambda message: message.text and (
    "youtube.com" in message.text.lower() or
    "youtu.be" in message.text.lower() or
    "m.youtube" in message.text.lower() or
    (message.text.startswith("http") and ("youtu" in message.text.lower()))
))
async def handle_video_link(message: types.Message):
    # Vérifier si l'utilisateur est banni
    user_id = message.from_user.id
    if await is_user_banned(user_id):
        await message.reply("❌ Vous êtes banni de ce bot.")
        return

    msg = await message.reply("🔄 Téléchargement en cours... Cela peut prendre quelques instants.")

    # Extraire l'URL YouTube
    url = message.text.strip()

    try:
        # Nettoyer l'URL
        url = url.strip()
        
        # Ajouter https:// si manquant
        if not url.startswith(('http://', 'https://')):
            if url.startswith('www.') or url.startswith('youtube.com') or url.startswith('youtu.be'):
                url = 'https://' + url
            elif url.startswith('m.youtube.com'):
                url = 'https://' + url
        
        # Vérifier que c'est bien un lien YouTube valide
        youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com', 'www.youtube.com', 'music.youtube.com']
        if not any(domain in url.lower() for domain in youtube_domains):
            await msg.edit_text("❌ Veuillez fournir un lien YouTube valide.\n\n"
                               "Formats acceptés:\n"
                               "• https://www.youtube.com/watch?v=...\n"
                               "• https://youtu.be/...\n"
                               "• https://m.youtube.com/watch?v=...\n"
                               "• https://music.youtube.com/watch?v=...")
            return

        # Essayer de télécharger la vidéo
        await msg.edit_text("📥 Récupération des informations de la vidéo...")

        video_path = download_video(url)

        if video_path and os.path.exists(video_path):
            # Logger le téléchargement réussi
            await log_download(user_id, url, success=True)
            # Vérifier la taille du fichier
            file_size = os.path.getsize(video_path) / (1024 * 1024)  # Taille en MB

            if file_size > 49:  # Telegram limite à 50MB
                await msg.edit_text(f"⚠️ La vidéo est trop grande ({file_size:.1f}MB). Telegram limite les fichiers à 50MB.")
                os.remove(video_path)
            elif file_size < 0.01:  # Fichier trop petit (moins de 10KB)
                await msg.edit_text("❌ Le fichier téléchargé semble corrompu ou trop petit.")
                os.remove(video_path)
            else:
                await msg.edit_text(f"📤 Envoi en cours... Taille: {file_size:.1f}MB")

                try:
                    await bot.send_video(
                        message.chat.id, 
                        video=types.FSInputFile(video_path),
                        caption="Voici votre vidéo! 🎬",
                        supports_streaming=True
                    )
                    await msg.delete()  # Supprimer le message de progression
                except Exception as send_error:
                    error_msg = str(send_error)
                    if "Request Entity Too Large" in error_msg or "413" in error_msg:
                        await msg.edit_text("❌ Fichier trop volumineux pour Telegram (limite 50MB)")
                    elif "Bad Request" in error_msg:
                        await msg.edit_text("❌ Format de fichier non supporté par Telegram")
                    else:
                        await msg.edit_text(f"❌ Erreur lors de l'envoi: {error_msg[:150]}")
                finally:
                    # Nettoyer le fichier dans tous les cas
                    try:
                        if os.path.exists(video_path):
                            os.remove(video_path)
                            print(f"Fichier nettoyé: {video_path}")
                    except Exception as cleanup_error:
                        print(f"Erreur nettoyage: {cleanup_error}")
        else:
            # Logger l'échec du téléchargement
            await log_download(user_id, url, success=False, error_msg="Impossible de télécharger la vidéo")
            
            # Essayer une approche alternative avec des formats audio
            await msg.edit_text("🔄 Tentative de téléchargement audio...")
            
            audio_opts = {
                'format': 'bestaudio[filesize<45M]/worst[filesize<45M]',
                'outtmpl': f"{uuid.uuid4()}.%(ext)s",
                'noplaylist': True,
                'quiet': True,
                'extract_flat': False,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            }
            
            try:
                with yt_dlp.YoutubeDL(audio_opts) as ydl:
                    ydl.download([url])
                    # Chercher le fichier audio téléchargé
                    for f in os.listdir('.'):
                        if f.startswith(audio_opts['outtmpl'].split('.')[0]):
                            if os.path.getsize(f) > 1024:
                                await bot.send_audio(
                                    message.chat.id,
                                    audio=types.FSInputFile(f),
                                    caption="🎵 Voici l'audio de la vidéo!"
                                )
                                os.remove(f)
                                await msg.delete()
                                return
                            else:
                                os.remove(f)
            except:
                pass
            
            await msg.edit_text(
                "❌ Impossible de télécharger cette vidéo.\n\n"
                "🔍 **Causes possibles:**\n"
                "• La vidéo est privée, supprimée ou restreinte\n"
                "• Restrictions géographiques actives\n"
                "• Vidéo protégée par le créateur\n"
                "• Problème temporaire de YouTube\n"
                "• Format de vidéo non supporté\n\n"
                "💡 **Solutions à essayer:**\n"
                "• Vérifier que la vidéo est publique\n"
                "• Essayer avec une vidéo différente\n"
                "• Réessayer dans quelques minutes\n"
                "• Utiliser un lien direct vers la vidéo\n\n"
                "📝 Si le problème persiste, contactez l'administrateur."
            )

    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
            await msg.edit_text(
                "🤖 **YouTube a détecté une activité automatisée.**\n\n"
                "🔄 **Solutions à essayer :**\n"
                "• Attendez 5-10 minutes avant de réessayer\n"
                "• Essayez avec une vidéo différente\n"
                "• Utilisez un lien plus court (youtu.be/...)\n"
                "• Vérifiez que la vidéo est publique\n\n"
                "⚠️ **Note :** Ce problème est temporaire et se résout automatiquement.",
                parse_mode="Markdown"
            )
        elif "Private video" in error_msg or "unavailable" in error_msg.lower():
            await msg.edit_text(
                "🔒 **Vidéo non accessible**\n\n"
                "Cette vidéo est soit :\n"
                "• Privée ou supprimée\n"
                "• Restreinte géographiquement\n"
                "• Non listée avec restrictions\n\n"
                "Essayez avec une autre vidéo publique."
            )
        elif "Video unavailable" in error_msg:
            await msg.edit_text(
                "📵 **Vidéo indisponible**\n\n"
                "Causes possibles :\n"
                "• Vidéo supprimée par l'auteur\n"
                "• Problème de copyright\n"
                "• Restriction d'âge\n\n"
                "Veuillez essayer avec une autre vidéo."
            )
        else:
            await msg.edit_text(f"❌ **Erreur technique :** {error_msg[:150]}...\n\n"
                               "Réessayez dans quelques minutes ou contactez l'administrateur.")

        print(f"Exception complète dans handle_video_link: {e}")

@dp.message(lambda message: message.text and message.text.startswith("/admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    admin_help = """
🛠 **Panneau Admin - Commandes disponibles:**

📢 `/broadcast [message]` - Diffuser un message à tous les utilisateurs
👮‍♂️ `/addadmin [user_id]` - Ajouter un admin
🚫 `/ban [user_id]` - Bannir un utilisateur
📊 `/stats` - Voir les statistiques du bot
🧹 `/videcache` - Vider le cache vidéo
📁 `/storage` - Voir le stockage

**Utilisation :** Tapez directement la commande avec les paramètres requis.
"""

    await message.answer(admin_help, parse_mode="Markdown")

# Classes pour les états de l'admin
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

class Announcement(StatesGroup):
    waiting_for_text = State()

class BanUser(StatesGroup):
    waiting_for_ban_id = State()

class UnbanUser(StatesGroup):
    waiting_for_unban_id = State()

class EditStartMessage(StatesGroup):
    waiting_for_new_message = State()

class ManageAdmins(StatesGroup):
    waiting_for_admin_id = State()

class ManageSubChannels(StatesGroup):
    waiting_for_channel_name = State()

class TelegraphImage(StatesGroup):
    waiting_for_image = State()

class ManageFormats(StatesGroup):
    waiting_for_format = State()

class ManageLinks(StatesGroup):
    waiting_for_link = State()
    waiting_for_name = State()

# Variables globales pour les utilisateurs
subscribers = set()
banned_users = set()
admin_ids = set(ADMIN_IDS)
welcome_message = "Bienvenue sur notre bot de téléchargement de vidéos YouTube !"
download_formats = {
    "best": "Meilleure qualité disponible",
    "480p": "Qualité moyenne (480p)",
    "audio": "Audio seulement"
}
important_links = {
    "Chaîne principale": "https://t.me/sineur_x_bot",
    "Support": "https://t.me/sineur_x_bot"
}

@dp.callback_query(lambda c: c.data and c.data.startswith("admin_"))
async def process_admin_callbacks(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer(text="Accès refusé.")
        return

    data = callback_query.data

    if data == "admin_broadcast":
        await state.set_state(Announcement.waiting_for_text)
        await bot.send_message(callback_query.from_user.id, "Envoyez le texte à diffuser à tous les utilisateurs.")

    elif data == "admin_addadmin":
        await state.set_state(ManageAdmins.waiting_for_admin_id)
        await state.update_data(action="add")
        await bot.send_message(callback_query.from_user.id, "Envoyez l'ID de l'utilisateur à ajouter comme admin.")

    elif data == "admin_banadmin":
        await state.set_state(BanUser.waiting_for_ban_id)
        await bot.send_message(callback_query.from_user.id, "Envoyez l'ID de l'utilisateur à bannir.")

    elif data == "admin_stats":
        db_stats = await get_user_stats()
        stats = (
            f"📊 **Statistiques du bot:**\n\n"
            f"👥 Nombre d'utilisateurs: {db_stats['total_users']}\n"
            f"📥 Total téléchargements: {db_stats['total_downloads']}\n"
            f"👮‍♂️ Nombre d'admins: {len(admin_ids)}\n"
            f"🚫 Nombre de bannis: {db_stats['banned_users']}"
        )
        await bot.send_message(callback_query.from_user.id, stats, parse_mode="Markdown")

    elif data == "admin_videcache":
        count = 0
        for f in os.listdir('.'):
            if f.endswith(".mp4") or f.endswith(".m4a"):
                try:
                    os.remove(f)
                    count += 1
                except Exception as e:
                    print(f"Erreur lors de la suppression de {f}: {e}")
        await bot.send_message(callback_query.from_user.id, f"🧹 Cache vidéo vidé : {count} fichiers supprimés.")

    elif data == "admin_storage":
        files = []
        total_size = 0

        for f in os.listdir('.'):
            try:
                size = os.path.getsize(f)
                total_size += size
                if f.endswith(('.mp4', '.m4a')):
                    files.append(f"📹 {f} ({size/1024/1024:.1f}MB)")
                else:
                    files.append(f"📄 {f} ({size/1024:.1f}KB)")
            except:
                files.append(f"❓ {f}")

        file_list = "\n".join(files[:20])  # Limiter à 20 fichiers
        if len(files) > 20:
            file_list += f"\n... et {len(files)-20} autres fichiers"

        storage_info = f"📁 **Stockage:**\n\n{file_list}\n\n**Taille totale:** {total_size/1024/1024:.1f}MB"
        await bot.send_message(callback_query.from_user.id, storage_info, parse_mode="Markdown")

    await callback_query.answer()

@dp.callback_query(lambda c: c.data in ["admin_add", "admin_remove"])
async def process_admin_manage(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data  # "admin_add" ou "admin_remove"
    await state.set_state(ManageAdmins.waiting_for_admin_id)

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="Annuler", callback_data="cancel_admin_action"))

    if action == "admin_add":
        await bot.send_message(callback_query.from_user.id, "Envoyez l'ID de l'utilisateur à ajouter comme admin.", reply_markup=keyboard)
        await state.update_data(action="add")
    else:
        await bot.send_message(callback_query.from_user.id, "Envoyez l'ID de l'utilisateur à supprimer des admins.", reply_markup=keyboard)
        await state.update_data(action="remove")

    await callback_query.answer()

@dp.message(ManageAdmins.waiting_for_admin_id)
async def manage_admins_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")

    try:
        # Vérification que le texte contient uniquement des chiffres
        if not message.text.strip().isdigit():
            await message.reply("ID invalide. Veuillez entrer un nombre entier positif.")
            return

        admin_id = int(message.text.strip())

        if action == "add":
            admin_ids.add(admin_id)
            await message.reply(f"Utilisateur {admin_id} ajouté comme admin.")
        elif action == "remove":
            if admin_id in admin_ids:
                admin_ids.remove(admin_id)
                await message.reply(f"Utilisateur {admin_id} supprimé des admins.")
            else:
                await message.reply(f"Utilisateur {admin_id} n'est pas admin.")
    except ValueError:
        await message.reply("ID invalide. Veuillez entrer un nombre entier positif.")
    except Exception as e:
        await message.reply(f"Erreur: {e}")

    await state.clear()

@dp.message(BanUser.waiting_for_ban_id)
async def ban_user_handler(message: types.Message, state: FSMContext):
    try:
        # Vérification que le texte contient uniquement des chiffres
        if not message.text.strip().isdigit():
            await message.reply("ID invalide. Veuillez entrer un nombre entier positif.")
            return

        user_id = int(message.text.strip())
        banned_users.add(user_id)

        if user_id in subscribers:
            subscribers.remove(user_id)

        await message.reply(f"Utilisateur {user_id} banni.")
    except ValueError:
        await message.reply("ID invalide. Veuillez entrer un nombre entier positif.")
    except Exception as e:
        await message.reply(f"Erreur: {e}")

    await state.clear()

@dp.message(UnbanUser.waiting_for_unban_id)
async def unban_user_handler(message: types.Message, state: FSMContext):
    try:
        # Vérification que le texte contient uniquement des chiffres
        if not message.text.strip().isdigit():
            await message.reply("ID invalide. Veuillez entrer un nombre entier positif.")
            return

        user_id = int(message.text.strip())

        if user_id in banned_users:
            banned_users.remove(user_id)
            await message.reply(f"Utilisateur {user_id} débanni.")
        else:
            await message.reply("Cet utilisateur n'est pas banni.")
    except ValueError:
        await message.reply("ID invalide. Veuillez entrer un nombre entier positif.")
    except Exception as e:
        await message.reply(f"Erreur: {e}")

    await state.clear()


# Commandes admin traditionnelles
@dp.message(lambda message: message.text and (message.text.startswith("/broadcast") or message.text.startswith("/diffuse")))
async def cmd_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    # Extraire le texte de l'annonce après la commande
    if message.text.startswith("/broadcast"):
        announcement_text = message.text.replace("/broadcast", "", 1).strip()
        cmd_name = "/broadcast"
        prefix = "📣 BROADCAST :\n\n"
    else:
        announcement_text = message.text.replace("/diffuse", "", 1).strip()
        cmd_name = "/diffuse"
        prefix = "📢 DIFFUSION :\n\n"

    if not announcement_text:
        await message.reply(f"Usage: {cmd_name} [votre message]")
        return

    # Procéder à l'envoi
    sent = 0
    failed = 0

    await message.reply("Envoi de l'annonce en cours...")

    # Assurons-nous que subscribers existe
    global subscribers
    if not hasattr(globals(), 'subscribers') or subscribers is None:
        subscribers = set()

    # Si subscribers est vide, on doit quand même tenter d'envoyer aux admins
    if not subscribers:
        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, f"{prefix}{announcement_text}")
                sent += 1
            except Exception as e:
                print(f"Erreur lors de l'envoi à l'admin {admin_id} : {e}")
                failed += 1
    else:
        for user_id in list(subscribers):
            if user_id not in banned_users:
                try:
                    await bot.send_message(user_id, f"{prefix}{announcement_text}")
                    sent += 1
                except Exception as e:
                    print(f"Erreur lors de l'envoi à {user_id} : {e}")
                    failed += 1

    await message.reply(f"✅ Annonce envoyée à {sent} utilisateurs.\n❌ {failed} échecs.")

@dp.message(lambda message: message.text and message.text.startswith("/ban"))
async def cmd_ban(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    try:
        user_id = int(message.text.replace("/ban", "", 1).strip())
        banned_users.add(user_id)

        if user_id in subscribers:
            subscribers.remove(user_id)

        await message.reply(f"Utilisateur {user_id} banni avec succès.")
    except ValueError:
        await message.reply("Usage: /ban [user_id]")
    except Exception as e:
        await message.reply(f"Erreur: {e}")

@dp.message(lambda message: message.text and message.text.startswith("/unban"))
async def cmd_unban(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    try:
        user_id = int(message.text.replace("/unban", "", 1).strip())

        if user_id in banned_users:
            banned_users.remove(user_id)
            await message.reply(f"Utilisateur {user_id} débanni avec succès.")
        else:
            await message.reply("Cet utilisateur n'est pas banni.")
    except ValueError:
        await message.reply("Usage: /unban [user_id]")
    except Exception as e:
        await message.reply(f"Erreur: {e}")

@dp.message(lambda message: message.text and message.text.startswith("/stats"))
async def cmd_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    stats = (
        f"📊 Statistiques du bot:\n\n"
        f"👥 Nombre d'utilisateurs: {len(subscribers)}\n"
        f"👮‍♂️ Nombre d'admins: {len(admin_ids)}\n"
        f"🚫 Nombre de bannis: {len(banned_users)}"
    )
    await message.reply(stats)

@dp.message(lambda message: message.text and message.text.startswith("/addadmin"))
async def cmd_add_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    try:
        user_id = int(message.text.replace("/addadmin", "", 1).strip())
        admin_ids.add(user_id)
        await message.reply(f"Utilisateur {user_id} ajouté comme admin.")
    except ValueError:
        await message.reply("Usage: /addadmin [user_id]")
    except Exception as e:
        await message.reply(f"Erreur: {e}")

@dp.message(lambda message: message.text and message.text.startswith("/removeadmin"))
async def cmd_remove_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    try:
        user_id = int(message.text.replace("/removeadmin", "", 1).strip())

        if user_id in admin_ids:
            admin_ids.remove(user_id)
            await message.reply(f"Utilisateur {user_id} supprimé des admins.")
        else:
            await message.reply("Cet utilisateur n'est pas admin.")
    except ValueError:
        await message.reply("Usage: /removeadmin [user_id]")
    except Exception as e:
        await message.reply(f"Erreur: {e}")

@dp.message(lambda message: message.text and message.text.startswith("/videcache"))
async def cmd_videcache(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    count = 0
    for f in os.listdir('.'):
        if f.endswith(".mp4") or f.endswith(".m4a"):
            try:
                os.remove(f)
                count += 1
            except Exception as e:
                await message.reply(f"Erreur lors de la suppression de {f}: {e}")

    await message.reply(f"🧹 Cache vidéo vidé : {count} fichiers supprimés.")

@dp.message(lambda message: message.text and message.text.startswith("/storage"))
async def cmd_storage(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

    files = []
    total_size = 0

    for f in os.listdir('.'):
        try:
            size = os.path.getsize(f)
            total_size += size
            if f.endswith(('.mp4', '.m4a')):
                files.append(f"📹 {f} ({size/1024/1024:.1f}MB)")
            else:
                files.append(f"📄 {f} ({size/1024:.1f}KB)")
        except:
            files.append(f"❓ {f}")

    file_list = "\n".join(files[:20])  # Limiter à 20 fichiers
    if len(files) > 20:
        file_list += f"\n... et {len(files)-20} autres fichiers"

    storage_info = f"📁 **Stockage:**\n\n{file_list}\n\n**Taille totale:** {total_size/1024/1024:.1f}MB"
    await message.reply(storage_info, parse_mode="Markdown")

@dp.message(lambda message: EditStartMessage.waiting_for_new_message and message.content_type == types.ContentType.TEXT)
async def edit_start_message_handler(message: types.Message, state: FSMContext):
    global welcome_message
    welcome_message = message.text
    await message.reply("Message de démarrage mis à jour.")
    await state.clear()

@dp.callback_query(lambda c: c.data in ["sub_add", "sub_remove"])
async def process_sub_manage(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data  # "sub_add" ou "sub_remove"
    await state.set_state(ManageSubChannels.waiting_for_channel_name)

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="Annuler", callback_data="cancel_admin_action"))

    if action == "sub_add":
        await bot.send_message(callback_query.from_user.id, "Envoyez le nom de la chaîne (sans @) à ajouter.", reply_markup=keyboard)
        await state.update_data(action="add")
    else:
        await bot.send_message(callback_query.from_user.id, "Envoyez le nom de la chaîne (sans @) à supprimer.", reply_markup=keyboard)
        await state.update_data(action="remove")

    await callback_query.answer()

@dp.message(lambda message: ManageSubChannels.waiting_for_channel_name and message.content_type == types.ContentType.TEXT)
async def manage_sub_channel_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")
    channel_name = message.text.strip()

    # Enlever le @ si l'utilisateur l'a inclus
    if channel_name.startswith('@'):
        channel_name = channel_name[1:]

    if action == "add":
        if channel_name not in FORCE_SUB_CHANNELS:
            FORCE_SUB_CHANNELS.append(channel_name)
            await message.reply(f"Chaîne {channel_name} ajoutée à l'abonnement forcé.")
        else:
            await message.reply("Cette chaîne est déjà dans la liste.")
    else:
        if channel_name in FORCE_SUB_CHANNELS:
            FORCE_SUB_CHANNELS.remove(channel_name)
            await message.reply(f"Chaîne {channel_name} supprimée de l'abonnement forcé.")
        else:
            await message.reply("Cette chaîne n'est pas dans la liste.")

    await state.clear()

@dp.message(lambda message: TelegraphImage.waiting_for_image and message.content_type == types.ContentType.PHOTO)
async def telegraph_image_handler(message: types.Message, state: FSMContext):
    photo = message.photo[-1]  # Prendre la plus grande taille disponible

    try:
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)

        temp_filename = f"{uuid.uuid4()}.jpg"
        with open(temp_filename, "wb") as f:
            f.write(downloaded_file.read())

        url = upload_image_to_telegraph(temp_filename)
        os.remove(temp_filename)

        if url:
            await message.reply(f"Image uploadée sur Telegraph : {url}")
        else:
            await message.reply("Erreur lors de l'upload sur Telegraph.")
    except Exception as e:
        await message.reply(f"Erreur : {e}")

    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_manage_formats")
async def admin_manage_formats(callback_query: types.CallbackQuery):
    # Afficher le menu de gestion des formats
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="Ajouter un format", callback_data="format_add"),
        types.InlineKeyboardButton(text="Supprimer un format", callback_data="format_remove"),
        types.InlineKeyboardButton(text="Retour", callback_data="back_to_admin")
    )
    await bot.send_message(callback_query.from_user.id, "Gérer les formats de téléchargement :", reply_markup=keyboard)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data in ["format_add", "format_remove"])
async def process_format_manage(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data
    await state.set_state(ManageFormats.waiting_for_format)

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="Annuler", callback_data="cancel_admin_action"))

    if action == "format_add":
        await bot.send_message(
            callback_query.from_user.id, 
            "Envoyez le format à ajouter au format 'code:description'.\nExemple: '720p:Qualité HD (720p)'", 
            reply_markup=keyboard
        )
        await state.update_data(action="add")
    else:
        format_list = "\n".join([f"{code}: {desc}" for code, desc in download_formats.items()])
        await bot.send_message(
            callback_query.from_user.id, 
            f"Formats disponibles:\n{format_list}\n\nEnvoyez le code du format à supprimer:", 
            reply_markup=keyboard
        )
        await state.update_data(action="remove")

    await callback_query.answer()

@dp.message(lambda message: ManageFormats.waiting_for_format and message.content_type == types.ContentType.TEXT)
async def manage_formats_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")

    if action == "add":
        try:
            code, description = message.text.split(":", 1)
            code = code.strip()
            description = description.strip()

            if code in download_formats:
                await message.reply(f"Le format '{code}' existe déjà. Utilisez un autre code.")
            else:
                download_formats[code] = description
                await message.reply(f"Format '{code}' ajouté avec succès.")
        except ValueError:
            await message.reply("Format invalide. Utilisez le format 'code:description'.")
    elif action == "remove":
        format_code = message.text.strip()

        if format_code in download_formats:
            del download_formats[format_code]
            await message.reply(f"Format '{format_code}' supprimé avec succès.")
        else:
            await message.reply(f"Format '{format_code}' introuvable.")

    await state.clear()

    # Afficher le menu de gestion des formats
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="Ajouter un format", callback_data="format_add"),
        types.InlineKeyboardButton(text="Supprimer un format", callback_data="format_remove"),
        types.InlineKeyboardButton(text="Retour", callback_data="back_to_admin")
    )
    await message.answer("Gérer les formats de téléchargement :", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "admin_manage_links")
async def admin_manage_links(callback_query: types.CallbackQuery):
    # Afficher le menu de gestion des liens
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="Ajouter un lien", callback_data="link_add"),
        types.InlineKeyboardButton(text="Supprimer un lien", callback_data="link_remove"),
                types.InlineKeyboardButton(text="Liste des liens", callback_data="link_list"),
        types.InlineKeyboardButton(text="Retour", callback_data="back_to_admin")
    )
    await bot.send_message(callback_query.from_user.id, "Gérer les liens importants :", reply_markup=keyboard)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data in ["link_add", "link_remove", "link_list"])
async def process_link_manage(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data

    if action == "link_list":
        link_list = "\n".join([f"• {name}: {url}" for name, url in important_links.items()])
        if link_list:
            await bot.send_message(callback_query.from_user.id, f"Liens importants:\n{link_list}")
        else:
            await bot.send_message(callback_query.from_user.id, "Aucun lien enregistré.")

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="Retour", callback_data="admin_manage_links"))
        await bot.send_message(callback_query.from_user.id, "Que souhaitez-vous faire ?", reply_markup=keyboard)
    else:
        if action == "link_add":
            await state.set_state(ManageLinks.waiting_for_name)
        else:
            await state.set_state(ManageLinks.waiting_for_link)

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(text="Annuler", callback_data="cancel_admin_action"))

        if action == "link_add":
            await bot.send_message(
                callback_query.from_user.id, 
                "Envoyez le nom du lien à ajouter:", 
                reply_markup=keyboard
            )
            await state.update_data(action="add")
        else:
            link_list = "\n".join([f"• {name}" for name in important_links.keys()])
            await bot.send_message(
                callback_query.from_user.id, 
                f"Liens disponibles:\n{link_list}\n\nEnvoyez le nom du lien à supprimer:", 
                reply_markup=keyboard
            )
            await state.update_data(action="remove")

    await callback_query.answer()

@dp.message(lambda message: ManageLinks.waiting_for_name and message.content_type == types.ContentType.TEXT)
async def manage_links_name_handler(message: types.Message, state: FSMContext):
    link_name = message.text.strip()

    if link_name in important_links:
        await message.reply(f"Le lien '{link_name}' existe déjà. Utilisez un autre nom.")
        return

    await state.update_data(link_name=link_name)
    await state.set_state(ManageLinks.waiting_for_link)

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="Annuler", callback_data="cancel_admin_action"))

    await message.reply("Maintenant, envoyez l'URL du lien:", reply_markup=keyboard)

@dp.message(lambda message: ManageLinks.waiting_for_link and message.content_type == types.ContentType.TEXT)
async def manage_links_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")

    if action == "add":
        link_name = data.get("link_name")
        link_url = message.text.strip()

        if not link_url.startswith(("http://", "https://", "t.me/")):
            await message.reply("URL invalide. Assurez-vous que l'URL commence par http://, https:// ou t.me/")
            return

        important_links[link_name] = link_url
        await message.reply(f"Lien '{link_name}' ajouté avec succès.")
    else:
        link_name = message.text.strip()

        if link_name in important_links:
            del important_links[link_name]
            await message.reply(f"Lien '{link_name}' supprimé avec succès.")
        else:
            await message.reply(f"Lien '{link_name}' introuvable.")

    await state.clear()

    # Afficher le menu de gestion des liens
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="Ajouter un lien", callback_data="link_add"),
        types.InlineKeyboardButton(text="Supprimer un lien", callback_data="link_remove"),
        types.InlineKeyboardButton(text="Liste des liens", callback_data="link_list"),
        types.InlineKeyboardButton(text="Retour", callback_data="back_to_admin")
    )
    await message.answer("Gérer les liens importants :", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "back_to_admin")
async def back_to_admin_panel(callback_query: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Envoyer une annonce", callback_data="admin_announce")],
            [types.InlineKeyboardButton(text="Gérer les admins", callback_data="admin_manage_admins")],
            [types.InlineKeyboardButton(text="Bannir utilisateur", callback_data="admin_ban_user")],
            [types.InlineKeyboardButton(text="Débannir utilisateur", callback_data="admin_unban_user")],
            [types.InlineKeyboardButton(text="Voir statistiques", callback_data="admin_stats")],
            [types.InlineKeyboardButton(text="Gérer formats", callback_data="admin_manage_formats")],
            [types.InlineKeyboardButton(text="Gérer liens", callback_data="admin_manage_links")],
            [types.InlineKeyboardButton(text="Voir stockage", callback_data="admin_storage")],
            [types.InlineKeyboardButton(text="Vider stockage", callback_data="admin_clear_storage")],
            [types.InlineKeyboardButton(text="Modifier message démarrage", callback_data="admin_edit_start")],
            [types.InlineKeyboardButton(text="Gérer abonnement forcé", callback_data="admin_manage_sub")],
            [types.InlineKeyboardButton(text="Gérer images Telegraph", callback_data="admin_manage_telegraph")]
        ]
    )
    await bot.send_message(callback_query.from_user.id, "Panneau Admin :", reply_markup=keyboard)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "check_sub")
async def handle_check_subscription(callback_query: types.CallbackQuery):
    """Gestionnaire pour le callback de vérification d'abonnement"""
    user_id = callback_query.from_user.id

    if await check_subscription(user_id, bot):
        await callback_query.answer("✅ Merci ! Vous pouvez maintenant utiliser le bot.")


# -------------------------------
# Handlers pour le serveur web - garde le bot en ligne
# -------------------------------
async def handle_index(request):
    return web.Response(text="Le bot est en ligne!")

@dp.message(lambda message: message.text and message.text.startswith("/ping"))
async def cmd_ping(message: types.Message):
    """
    Commande simple pour vérifier si le bot est en ligne.
    Utile pour tester la disponibilité du bot après déploiement.
    """
    response_time = await message.reply("Pong! Le bot est en ligne.")
    # Calculer le temps de réponse
    ping_time = (response_time.date - message.date).total_seconds()
    await response_time.edit_text(f"Pong! Le bot est en ligne.\nTemps de réponse: {ping_time:.2f}s")

# -------------------------------
# Lancement du bot
# -------------------------------
async def main():
    # Initialize global variables
    global subscribers, banned_users, admin_ids
    subscribers = set()
    banned_users = set()
    admin_ids = set(ADMIN_IDS)

    # Clean up any temp files from previous runs
    try:
        for f in os.listdir('.'):
            if f.endswith((".mp4", ".m4a", ".webm", ".mkv")):
                try:
                    os.remove(f)
                    print(f"Supprimé: {f}")
                except:
                    pass
    except Exception as e:
        print(f"Erreur lors du nettoyage: {e}")

    # Arrêter toutes les instances précédentes du bot avec délai
    try:
        print("🔄 Arrêt des instances précédentes...")
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.close()
        await asyncio.sleep(5)  # Attendre 5 secondes pour éviter les conflits
        print("✅ Webhook supprimé et mises à jour en attente effacées")
        
        # Recréer l'instance du bot
        global bot
        bot = Bot(token=BOT_TOKEN)
    except Exception as e:
        print(f"Erreur lors de la suppression du webhook: {e}")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Créer une application web pour garder le bot en ligne
    app = web.Application()
    app.router.add_get('/', handle_index)

    # Démarrer le serveur web en arrière-plan
    port = os.environ.get('PORT', 8080)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    print("🚀 Bot démarré! Le bot est prêt à recevoir des commandes.")
    print(f"✅ Serveur web démarré sur http://0.0.0.0:{port}")
    repl_slug = os.environ.get('REPL_SLUG', 'workspace')
    repl_owner = os.environ.get('REPL_OWNER', 'user')
    print(f"✅ URL de webhook: https://{repl_slug}.{repl_owner}.repl.co")

    # Attendre avant de démarrer le polling pour éviter les conflits
    print("⏳ Attente de 3 secondes pour éviter les conflits...")
    await asyncio.sleep(3)
    
    # Démarrer le bot avec gestion d'erreurs
    try:
        print("🔄 Démarrage du polling...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        print(f"❌ Erreur lors du démarrage du polling: {e}")
        await asyncio.sleep(10)
        print("🔄 Nouvelle tentative...")
        await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())