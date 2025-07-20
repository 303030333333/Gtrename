import logging
import os
import uuid
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
import yt_dlp
from telegraph import Telegraph
from aiohttp import web
# -------------------------------
# Configuration
# -------------------------------
BOT_TOKEN = "7771993655:AAEsuPrx3vn34Ql4ws_k6pPXj91X1uecaAM"  # Remplace par ton token BotFather
ADMIN_IDS = [5116530698]  # Remplace par tes IDs admin
FORCE_SUB_CHANNELS = ["sineur_x_bot"]  # Remplace par le(s) nom(s) de ta(tes) chaîne(s)
WELCOME_IMAGE_URL = "https://graph.org/file/a832e964b6e04f82c1c75-7a8ca2206c069a333a.jpg"  # URL de ton image de bienvenue

# -------------------------------
# Initialisation du bot
# -------------------------------
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=MemoryStorage())
  # Ne pas échouer silencieusement, indiquer l'erreur

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
            chat = await bot.get_chat(f"@{channel}")
            member = await bot.get_chat_member(chat.id, user_id)

            if member.status in [
                ChatMemberStatus.LEFT,
                ChatMemberStatus.KICKED,
                ChatMemberStatus.BANNED
            ]:
                not_subscribed.append(channel)

        except Exception as e:
            print(f"Erreur lors de la vérification pour @{channel} :", e)
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
    #g
    @dp.message(Command("start"))
async def cmd_start(message: types.Message, bot: Bot):
    user_id = message.from_user.id

    if not await check_subscription(user_id, bot):  # ✅ Appel corrigé
        return

    await message.answer("Bienvenue ! Envoie-moi un lien YouTube.")
    # Extraction de l'ID de la vidéo à partir de différents formats d'URL
    video_id = None
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0].split("&")[0]
    elif "youtube.com/watch" in url and "v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "youtube.com/shorts/" in url:
        video_id = url.split("shorts/")[1].split("?")[0]

    if not video_id:
        print(f"Impossible d'extraire l'ID de la vidéo depuis l'URL: {url}")
        return None

    print(f"ID vidéo extrait: {video_id}")
    clean_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"URL normalisée: {clean_url}")

    output_filename = f"{uuid.uuid4()}.mp4"

    # Configuration de base pour yt-dlp
    ydl_opts = {
        # Format progressif pour éviter la nécessité de fusion audio/vidéo
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
        'outtmpl': output_filename,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': False,
        'verbose': True,
        'no_warnings': False,
        'ignoreerrors': True,
        'geo_bypass': True,
        'socket_timeout': 30,
        'nocheckcertificate': True,  # Ignorer les erreurs de certificat
        'prefer_insecure': True,     # Préférer les connexions non-sécurisées si nécessaire
        'extractor_retries': 5,      # Nombre de tentatives pour l'extraction
        'fragment_retries': 10,      # Nombre de tentatives pour le téléchargement de fragments
        'skip_unavailable_fragments': True,  # Ignorer les fragments non disponibles
        # Tenter de forcer IPv4 pour éviter les restrictions
        'source_address': '0.0.0.0', 
    }

    for attempt in range(3):  # Faire 3 tentatives avec différentes configurations
        try:
            print(f"Tentative {attempt+1} de téléchargement depuis: {clean_url}")

            # Ajuster les options en fonction de la tentative
            if attempt == 1:
                # Deuxième tentative: essayer un format plus bas
                ydl_opts['format'] = 'best[height<=480]/best'
            elif attempt == 2:
                # Troisième tentative: essayer le format le plus simple
                ydl_opts['format'] = 'best'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"Téléchargement avec options: {ydl_opts['format']}")
                # Télécharger directement sans vérification préalable des infos
                ydl.download([clean_url])

                # Vérifier si le fichier existe
                if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
                    print(f"Téléchargement réussi: {output_filename}")
                    return output_filename
                else:
                    print(f"Le fichier {output_filename} n'existe pas ou est vide après la tentative {attempt+1}")

        except Exception as e:
            print(f"Erreur lors de la tentative {attempt+1}: {e}")
            # Continuer avec la prochaine tentative

    # Une dernière tentative avec YouTube-DL directement si toutes les autres ont échoué
    try:
        print("Dernière tentative avec une configuration alternative...")
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_filename,
            'noplaylist': True,
            'quiet': False,
            'verbose': True,
            'no_warnings': False,
            'ignoreerrors': True,
            'geo_bypass': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
                print(f"Téléchargement réussi avec la configuration alternative: {output_filename}")
                return output_filename
    except Exception as e:
        print(f"Échec de la dernière tentative: {e}")

    # Si on arrive ici, toutes les tentatives ont échoué
    print("Toutes les tentatives de téléchargement ont échoué.")
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
# Handlers du bot
# -------------------------------
@dp.message(lambda message: message.text and message.text.startswith("/start"))
async def cmd_start(message: types.Message):
    # Ajouter l'utilisateur à la liste des abonnés s'il n'est pas banni
    user_id = message.from_user.id
    if user_id not in banned_users:
        subscribers.add(user_id)

    # Vérifie l'abonnement forcé
    if not await check_subscription(user_id):
        await message.reply("Pour utiliser le bot, vous devez être abonné à notre chaîne.")
        return
    # Création du clavier inline
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Télécharger une vidéo", callback_data="download_video"),
                types.InlineKeyboardButton(text="Panneau Admin", callback_data="admin_panel")
            ]
        ]
    )
    # Envoi de l'image de bienvenue et du message
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=WELCOME_IMAGE_URL,
        caption=("Bienvenue sur notre bot de téléchargement de vidéos YouTube ! 📱\n\n"
                "Ce bot vous permet de télécharger facilement des vidéos depuis YouTube.\n\n"
                "✅ Téléchargement rapide\n"
                "✅ Haute qualité\n"
                "✅ Simple à utiliser\n\n"
                "Choisissez une option ci-dessous pour commencer :"),
        reply_markup=keyboard
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

@dp.message(lambda message: message.text and (message.text.startswith("http") or "youtu" in message.text))
async def handle_video_link(message: types.Message):
    msg = await message.reply("Téléchargement en cours... Cela peut prendre quelques instants.")

    # Extraire l'URL YouTube
    url = message.text.strip()

    try:
        # Essayer de télécharger la vidéo
        await message.reply("Récupération des informations de la vidéo...")
        video_path = download_video(url)

        if video_path and os.path.exists(video_path):
            # Vérifier la taille du fichier
            file_size = os.path.getsize(video_path) / (1024 * 1024)  # Taille en MB

            if file_size > 49:  # Telegram limite à 50MB
                await message.reply(f"⚠️ La vidéo est trop grande ({file_size:.1f}MB). Telegram limite les fichiers à 50MB.")
                os.remove(video_path)
            else:
                await message.reply(f"Envoi en cours... Taille: {file_size:.1f}MB")
                await bot.send_video(
                    message.chat.id, 
                    video=types.FSInputFile(video_path),
                    caption="Voici votre vidéo! 🎬"
                )
                await msg.delete()  # Supprimer le message "Téléchargement en cours"
                os.remove(video_path)
        else:
            await message.reply("⚠️ Impossible de télécharger cette vidéo. Vérifiez que l'URL est valide et que la vidéo est disponible.")
    except Exception as e:
        await message.reply(f"❌ Erreur: {str(e)[:200]}")
        print(f"Exception complète: {e}")

@dp.message(lambda message: message.text and message.text.startswith("/admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("Vous n'êtes pas autorisé à utiliser cette commande.")
        return

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
    await message.answer("Panneau Admin :", reply_markup=keyboard)

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

    if data == "admin_announce":
        await state.set_state(Announcement.waiting_for_text)
        await bot.send_message(callback_query.from_user.id, "Envoyez le texte de l'annonce à diffuser.")

    elif data == "admin_manage_admins":
        # Afficher la liste des admins actuels
        admin_list = "\n".join([f"• {admin_id}" for admin_id in admin_ids])

        # Créer le clavier pour ajouter/supprimer des admins
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(text="Ajouter un admin", callback_data="admin_add"),
            types.InlineKeyboardButton(text="Supprimer un admin", callback_data="admin_remove"),
            types.InlineKeyboardButton(text="Retour", callback_data="back_to_admin")
        )

        # Envoyer le message avec la liste des admins et le clavier
        await bot.send_message(
            callback_query.from_user.id, 
            f"Liste des admins actuels:\n{admin_list}\n\nChoisissez une action :",
            reply_markup=keyboard
        )

    elif data == "admin_ban_user":
        await state.set_state(BanUser.waiting_for_ban_id)
        await bot.send_message(callback_query.from_user.id, "Envoyez l'ID de l'utilisateur à bannir.")

    elif data == "admin_unban_user":
        await state.set_state(UnbanUser.waiting_for_unban_id)
        await bot.send_message(callback_query.from_user.id, "Envoyez l'ID de l'utilisateur à débannir.")

    elif data == "admin_stats":
        stats = (
            f"Nombre d'utilisateurs: {len(subscribers)}\n"
            f"Nombre d'admins: {len(admin_ids)}\n"
            f"Nombre de bannis: {len(banned_users)}"
        )
        await bot.send_message(callback_query.from_user.id, stats)

    elif data == "admin_manage_formats":
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(text="Ajouter un format", callback_data="format_add"),
            types.InlineKeyboardButton(text="Supprimer un format", callback_data="format_remove"),
            types.InlineKeyboardButton(text="Retour", callback_data="back_to_admin")
        )
        await bot.send_message(callback_query.from_user.id, "Gérer les formats de téléchargement :", reply_markup=keyboard)

    elif data == "admin_manage_links":
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(text="Ajouter un lien", callback_data="link_add"),
            types.InlineKeyboardButton(text="Supprimer un lien", callback_data="link_remove"),
            types.InlineKeyboardButton(text="Liste des liens", callback_data="link_list"),
            types.InlineKeyboardButton(text="Retour", callback_data="back_to_admin")
        )
        await bot.send_message(callback_query.from_user.id, "Gérer les liens importants :", reply_markup=keyboard)

    elif data == "admin_storage":
        files = os.listdir('.')
        await bot.send_message(callback_query.from_user.id, f"Fichiers présents: {files}")

    elif data == "admin_clear_storage":
        count = 0
        for f in os.listdir('.'):
            if f.endswith(".mp4") or f.endswith(".m4a"):
                os.remove(f)
                count += 1
        await bot.send_message(callback_query.from_user.id, f"{count} fichiers supprimés.")

    elif data == "admin_edit_start":
        await state.set_state(EditStartMessage.waiting_for_new_message)
        await bot.send_message(callback_query.from_user.id, "Envoyez le nouveau message de démarrage.")

    elif data == "admin_manage_sub":
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(text="Ajouter une chaîne", callback_data="sub_add"),
            types.InlineKeyboardButton(text="Supprimer une chaîne", callback_data="sub_remove")
        )
        await bot.send_message(callback_query.from_user.id, "Choisissez une action :", reply_markup=keyboard)

    elif data == "admin_manage_telegraph":
        await state.set_state(TelegraphImage.waiting_for_image)
        await bot.send_message(callback_query.from_user.id, "Envoyez l'image à uploader sur Telegraph.")

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

@dp.message(lambda message: message.text and message.text.startswith("/clean"))
async def cmd_clean(message: types.Message):
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

    await message.reply(f"✅ {count} fichiers supprimés.")

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

@dp.callback_query(lambda c: c.data == "cancel_admin_action")
async def cancel_admin_action(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await bot.send_message(callback_query.from_user.id, "Action annulée.")
    await back_to_admin_panel(callback_query)

@dp.message(Announcement.waiting_for_text)
async def announcement_handler(message: types.Message, state: FSMContext):
    announcement_text = message.text
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
                await bot.send_message(admin_id, f"📢 ANNONCE :\n\n{announcement_text}")
                sent += 1
            except Exception as e:
                print(f"Erreur lors de l'envoi à l'admin {admin_id} : {e}")
                failed += 1
    else:
        for user_id in list(subscribers):  # Utiliser list() au lieu de copy() pour éviter les erreurs
            if user_id not in banned_users:  # Ne pas envoyer aux utilisateurs bannis
                try:
                    await bot.send_message(user_id, f"📢 ANNONCE :\n\n{announcement_text}")
                    sent += 1
                except Exception as e:
                    print(f"Erreur lors de l'envoi à {user_id} : {e}")
                    failed += 1

    await message.reply(f"✅ Annonce envoyée à {sent} utilisateurs.\n❌ {failed} échecs.")
    await state.clear()

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
    for f in os.listdir('.'):
        if f.endswith(".mp4") or f.endswith(".m4a"):
            try:
                os.remove(f)
            except:
                pass

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
    print(f"✅ URL de webhook: https://{os.environ.get('REPL_SLUG')}.{os.environ.get('REPL_OWNER')}.repl.co")

    # Démarrer le bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())