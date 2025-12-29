import os
import subprocess
from telegram import InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder,CommandHandler,MessageHandler,CallbackQueryHandler,filters

TOKEN = "8529591713:AAECCE1g9EGlSKnMahyiYHrnZ36zXrwyWuI"
CHANNEL = -1003550027843
VIDEO_FOLDER = "Video"

os.makedirs(VIDEO_FOLDER, exist_ok=True)

pending = {}
progress_msg = {}

def progress_bar(done, total, size=10):
    if total == 0:
        return "[░░░░░░░░░░] 0%"
    filled = int(size * done / total)
    percent = int((done / total) * 100)
    return f"[{'█'*filled}{'░'*(size-filled)}] {percent}%"

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

async def start(update, context):
    await update.message.reply_text(
        "🎥 Envoie une vidéo\n"
        "👉 Choisis le format\n"
        "✏️ Envoie le titre\n"
        "📤 Publication automatique"
    )

async def status(update, context):
    user_id = update.message.from_user.id
    done = context.user_data.get("done", 0)
    waiting = len(pending.get(user_id, []))
    total = done + waiting

    if total == 0:
        await update.message.reply_text("📭 Rien en cours.")
        return

    await update.message.reply_text(
        f"📊 Progression\n{progress_bar(done, total)}"
    )

async def receive_video(update,context):
    user_id = update.message.from_user.id
    video = update.message.video

    file = await video.get_file()
    video_path = f"{VIDEO_FOLDER}/{video.file_unique_id}.mp4"
    await file.download_to_drive(video_path)

    thumb_path = generate_thumbnail(video_path)

    pending.setdefault(user_id, []).append({
        "path": video_path,
        "thumb": thumb_path,
        "format": None
    })

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎥 Vidéo", callback_data="video"),
        InlineKeyboardButton("📄 Document", callback_data="document")
    ]])

    await update.message.reply_text(
        "📤 Vidéo reçue\n👉 Choisis le format :",
        reply_markup=keyboard
    )

async def choose_format(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id not in pending or not pending[user_id]:
        return

    pending[user_id][-1]["format"] = query.data
    await query.message.reply_text("✏️ Envoie le titre.")

async def receive_title(update, context):
    user_id = update.message.from_user.id
    if user_id not in pending or not pending[user_id]:
        return

    data = pending[user_id][0]
    if data["format"] is None:
        await update.message.reply_text("⚠️ Choisis le format.")
        return

    title = update.message.text.strip()
    safe_title = title.replace(" ", "_")

    video_path = data["path"]
    thumb_path = data["thumb"]

    with open(video_path, "rb") as f:

        if data["format"] == "video":
            await context.bot.send_video(
                chat_id=CHANNEL,
                video=f,
                caption=title,
                supports_streaming=True
            )

        else:
            # 1️⃣ vignette
            if thumb_path and os.path.exists(thumb_path):
                with open(thumb_path, "rb") as img:
                    await context.bot.send_photo(
                        chat_id=CHANNEL,
                        photo=img,
                        caption=title
                    )

            # 2️⃣ fichier
            await context.bot.send_document(
                chat_id=CHANNEL,
                document=f,
                filename=f"{safe_title}.mp4"
            )

    # nettoyage
    os.remove(video_path)
    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)

    pending[user_id].pop(0)
    context.user_data["done"] = context.user_data.get("done", 0) + 1

    done = context.user_data["done"]
    waiting = len(pending.get(user_id, []))
    total = done + waiting

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

    await update.message.reply_text("✅ Publié avec succès.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.VIDEO, receive_video))
    app.add_handler(CallbackQueryHandler(choose_format))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title))

    print("🤖 Bot démarré...")
    app.run_polling()

main()
