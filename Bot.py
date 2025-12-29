import os
import subprocess
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder,CommandHandler,MessageHandler,CallbackQueryHandler,filters

# ================= CONFIG =================
TOKEN = "8529591713:AAECCE1g9EGlSKnMahyiYHrnZ36zXrwyWuI"
CHANNEL = -1003550027843  
VIDEO_FOLDER = "Video"
os.makedirs(VIDEO_FOLDER, exist_ok=True)

pending = {}
progress_msg = {}

def progress_bar(done, total, size=10):
    filled = int(size * done / total) if total else 0
    empty = size - filled
    percent = int((done / total) * 100) if total else 0
    return f"[{'█'*filled}{'░'*empty}] {percent}%"

def generate_thumbnail(video_path):
    thumb_path = video_path.replace(".mp4", ".jpg")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", "00:00:01",
            "-vframes", "1",
            thumb_path
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return thumb_path

async def start(update,context):
    await update.message.reply_text(
        "🎥 Envoie une ou plusieurs vidéos\n"
        "📌 Pour chaque vidéo :\n"
        "1️⃣ Choisis le format\n"
        "2️⃣ Envoie le titre"
    )

async def status(update,context):
    user_id = update.message.from_user.id
    total_pending = len(pending.get(user_id, []))
    done = context.user_data.get("done", 0)

    if total_pending == 0 and done == 0:
        await update.message.reply_text("📭 Aucune vidéo en cours.")
        return

    bar = progress_bar(done, done + total_pending)
    await update.message.reply_text(
        f"📊 Statut\n"
        f"Traitée : {done} / {done + total_pending}\n"
        f"{bar}"
    )

async def receive_video(update, context):
    user_id = update.message.from_user.id

    if update.message.video:
        media = update.message.video
    elif update.message.document and update.message.document.mime_type.startswith("video"):
        media = update.message.document
    else:
        return

    file = await media.get_file()
    path = f"{VIDEO_FOLDER}/{media.file_unique_id}.mp4"
    await file.download_to_drive(path)

    pending.setdefault(user_id, []).append({
        "path": path,
        "format": None
    })

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎥 Vidéo", callback_data="video"),
            InlineKeyboardButton("📄 Document", callback_data="document")
        ]
    ])

    await update.message.reply_text(
        "📤 Vidéo reçue\nChoisis le format :",
        reply_markup=keyboard
    )


async def choose_format(update,context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    pending[user_id][-1]["format"] = query.data

    await query.message.reply_text("✏️ Envoie maintenant le titre.")

async def receive_title(update,context):
    user_id = update.message.from_user.id

    if user_id not in pending or not pending[user_id]:
        return

    video_data = pending[user_id][0]
    if video_data["format"] is None:
        await update.message.reply_text("⚠️ Choisis d’abord le format.")
        return

    title = update.message.text
    path = video_data["path"]
    filename = f"{title}.mp4"

    with open(path, "rb") as video_file:
        if video_data["format"] == "video":
            await context.bot.send_video(
                chat_id=CHANNEL,
                video=video_file,
                caption=title,
                supports_streaming=True,
                protect_content=True
            )
        else:
            thumb = generate_thumbnail(path)
            with open(thumb, "rb") as t:
                await context.bot.send_document(
                    chat_id=CHANNEL,
                    document=video_file,
                    thumb=t,
                    caption=title,
                    filename=filename,
                    protect_content=True
                )
            os.remove(thumb)

    os.remove(path)
    pending[user_id].pop(0)

    context.user_data["done"] = context.user_data.get("done", 0) + 1
    done = context.user_data["done"]
    total = done + len(pending.get(user_id, []))
    bar = progress_bar(done, total)

    if user_id not in progress_msg:
        msg = await update.message.reply_text(f"📈 Progression\n{bar}")
        progress_msg[user_id] = msg.message_id
    else:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=progress_msg[user_id],
            text=f"📈 Progression\n{bar}"
        )

    await update.message.reply_text("✅ Publication terminée.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("status",status))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO,receive_video))
    app.add_handler(CallbackQueryHandler(choose_format))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,receive_title))

    print("🤖 Bot Telegram lancé avec succès")
    app.run_polling()

main()
