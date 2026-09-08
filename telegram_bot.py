"""
بوت تليجرام مساعد شخصي - مربوط بـ Google Gemini (مجاني)
=========================================================

قبل التشغيل، لازم تركب المكتبات التالية:
pip install python-telegram-bot google-generativeai flask --break-system-packages

وتحط المفاتيح في متغيرات البيئة (Environment Variables):
TELEGRAM_BOT_TOKEN  -> توكن البوت من BotFather
GEMINI_API_KEY      -> مفتاح Gemini من Google AI Studio

ملاحظة: هذا الكود مجهز يشتغل كـ "Web Service" مجاني على Render.
فيه سيرفر صغير (Flask) يشتغل بالتوازي مع البوت، عشان Render
يقدر يتأكد إن الخدمة شغالة، وعشان تقدر تستخدم UptimeRobot
لإبقاء البوت صاحي (بدون نوم) مجاناً.
"""

import os
import logging
import threading
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------- الإعدادات ----------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))  # Render يعطي رقم البورت تلقائياً

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError(
        "لازم تحط TELEGRAM_BOT_TOKEN و GEMINI_API_KEY كمتغيرات بيئة قبل التشغيل!"
    )

# إعداد Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")  # نموذج سريع ومجاني

# إعداد تسجيل الأحداث (اختياري، يساعدك تشوف الأخطاء)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# نحتفظ بذاكرة محادثة بسيطة لكل مستخدم (تختفي إذا البوت أعاد التشغيل)
user_sessions = {}


# ---------- سيرفر صغير يبقي الخدمة "شغالة" حسب Render ----------
web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "البوت شغال! ✅"


def run_web_server():
    web_app.run(host="0.0.0.0", port=PORT)


# ---------- أوامر البوت ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id] = model.start_chat(history=[])
    await update.message.reply_text(
        "أهلاً فيك! 👋\n"
        "أنا مساعدك الشخصي، اسألني عن أي شي - ألعاب، برمجة، أو أي معلومة تبغاها.\n\n"
        "أوامر مفيدة:\n"
        "/start - يبدأ محادثة جديدة (ينسى القديمة)\n"
        "/help - يعرض هذي الرسالة"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "بس اكتب سؤالك عادي وأنا بجاوبك.\n"
        "لو تبغى تبدأ محادثة جديدة استخدم /start"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in user_sessions:
        user_sessions[user_id] = model.start_chat(history=[])

    chat = user_sessions[user_id]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = chat.send_message(user_text)
        reply_text = response.text
    except Exception as e:
        logging.error(f"خطأ من Gemini: {e}")
        reply_text = "عذراً، صار خطأ بسيط، جرب مرة ثانية بعد شوي 🙏"

    for i in range(0, len(reply_text), 4000):
        await update.message.reply_text(reply_text[i:i + 4000])


# ---------- تشغيل البوت ----------
def main():
    # نشغل سيرفر Flask بخيط منفصل (thread) عشان يشتغل بالتوازي مع البوت
    threading.Thread(target=run_web_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ البوت شغال الحين...")
    app.run_polling()


if __name__ == "__main__":
    main()
