from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد.")
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['/add_recipe', '/search_recipes'],
        ['/my_favorites', '/calculate_bmi'],
        ['/view_by_category', '/help']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "به سیستم مدیریت دستور پخت خوش آمدید!\n\n"
        "🔹 افزودن دستور پخت جدید\n"
        "🔹 جستجو در دستورها\n"
        "🔹 محاسبه BMI و دریافت پیشنهادات شخصی\n"
        "🔹 ذخیره در علاقه‌مندی‌ها\n"
        "🔹 نظر دادن روی دستورها\n"
        "🔹 مشاهده زمان پخت و سطح دشواری",
        reply_markup=reply_markup
    )