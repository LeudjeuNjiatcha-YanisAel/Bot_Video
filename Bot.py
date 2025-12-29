import os
from telegram import InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder,CommandHandler,MessageHandler,CallbackQueryHandler,filters

TOKEN = "8529591713:AAECCE1g9EGlSKnMahyiYHrnZ36zXrwyWuI"
CHANNEL = -1003550027843

VIDEO_FOLDER = "Video"
os.makedirs(VIDEO_FOLDER, exist_ok=True)

pending = {}
progress_msg = {}

def progress_bar(done, total, size=10):
    filled = int(size * done / total)
    empty = size - filled
    percent = int((done / total) * 100)
    return f"[{'█'*filled}{'░'*empty}] {percent}%"

async def start(update,context):
    await update.message.reply_text(
        "🎥 Envoie-moi plusieurs vidéos.\n"
        "📌 Pour chacune : format → titre → publication."
    )

async def status(update,context):
    user_id = update.message.from_user.id

    if user_id not in pending or not pending[user_id]:
        await update.message.reply_text("📭 Aucune vidéo en attente.")
        return

    total = len(pending[user_id])
    done = context.user_data.get("done", 0)

    bar = progress_bar(done, total + done)

    await update.message.reply_text(
        f"📊 Statut\n"
        f"Traitée : {done} / {done + total}\n"
        f"{bar}"
    )

async def receive_video(update,context):
    user_id = update.message.from_user.id
    video = update.message.video
    file = await video.get_file()

    path = f"{VIDEO_FOLDER}/{video.file_unique_id}.mp4"
    await file.download_to_drive(path)

    pending.setdefault(user_id, []).append({
        "path": path,
        "format": None
    })

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎥 Vidéo",callback_data="video"),
            InlineKeyboardButton("📄 Document",callback_data="document")
        ]
    ])

    await update.message.reply_text(
        "📤 Vidéo reçue.\nChoisis le format :",
        reply_markup=keyboard
    )

async def choose_format(update,context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    pending[user_id][-1]["format"] = query.data

    await query.message.reply_text("✏️ Envoie le titre.")

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
    total = len(pending[user_id]) + context.user_data.get("done",0)

    with open(path, "rb") as f:
        if video_data["format"] == "video":
            await context.bot.send_video(
                chat_id=CHANNEL,
                video=f,
                caption=title,
                supports_streaming=True
            )
        else:
            await context.bot.send_document(
                chat_id=CHANNEL,
                document=f,
                caption=title
            )

    os.remove(path)
    pending[user_id].pop(0)

    context.user_data["done"] = context.user_data.get("done",0) + 1
    done = context.user_data["done"]

    bar = progress_bar(done, total)

    # message progression
    if user_id not in progress_msg:
        msg = await update.message.reply_text(f"📈 Progression\n{bar}")
        progress_msg[user_id] = msg.message_id
    else:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=progress_msg[user_id],
            text=f"📈 Progression\n{bar}"
        )

    await update.message.reply_text("✅ Vidéo publiée.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("status",status))
    app.add_handler(MessageHandler(filters.VIDEO,receive_video))
    app.add_handler(CallbackQueryHandler(choose_format))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,receive_title))

    print("🤖 FodouopBot  démarré...")
    app.run_polling()

main()
