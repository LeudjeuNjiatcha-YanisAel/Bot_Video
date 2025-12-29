import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8529591713:AAECCE1g9EGlSKnMahyiYHrnZ36zXrwyWuI"
CHANNEL = "-1003550027843"

VIDEO_FOLDER = "Video"
os.makedirs(VIDEO_FOLDER, exist_ok=True)

pending = {}

async def start(update,context):
    await update.message.reply_text(
        "🎥 Envoie-moi une vidéo.\n"
        "✏️ Ensuite, envoie le titre pour la publier dans le canal."
    )

async def receive_video(update,context):
    video = update.message.video
    file = await video.get_file()

    path = f"{VIDEO_FOLDER}/{video.file_unique_id}.mp4"
    await file.download_to_drive(path)

    pending[update.message.from_user.id] = path

    await update.message.reply_text(
        "✅ Vidéo reçue.\n"
        "✏️ Envoie maintenant le nom de la vidéo."
    )

async def receive_title(update,context):
    user_id = update.message.from_user.id

    if user_id not in pending:
        return

    title = update.message.text
    video_path = pending[user_id]

    with open(video_path, "rb") as video:
        await context.bot.send_video(
            chat_id=CHANNEL,
            video=video,
            caption=title,
            supports_streaming=True
        )

    del pending[user_id]
    os.remove(video_path)

    await update.message.reply_text("📤 Vidéo publiée avec succès.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, receive_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title))

    print("🤖 Bot vidéo démarré...")
    app.run_polling()

if __name__ == "__main__":
    main()

