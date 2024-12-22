from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database.db_operations import DatabaseManager

# States for BMI conversation
BMI_HEIGHT, BMI_WEIGHT = range(2)

# Initialize database manager
db = DatabaseManager()

async def calculate_bmi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لطفاً قد خود را به سانتی‌متر وارد کنید:")
    return BMI_HEIGHT

async def receive_bmi_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = float(update.message.text)
        context.user_data['height'] = height
        await update.message.reply_text("لطفاً وزن خود را به کیلوگرم وارد کنید:")
        return BMI_WEIGHT
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
        return BMI_HEIGHT

async def receive_bmi_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text)
        height = context.user_data['height'] / 100  # convert cm to m
        bmi = weight / (height * height)
        
        if db.save_user_bmi(update.effective_user.id, bmi):
            message = f"شاخص BMI شما: {bmi:.1f}\n\n"
            if bmi < 18.5:
                message += "پیشنهاد: تمرکز روی غذاهای پرپروتئین و پرکالری."
            elif bmi < 25:
                message += "پیشنهاد: حفظ رژیم غذایی متعادل با تنوع در دستورها."
            else:
                message += "پیشنهاد: تمرکز روی غذاهای کم‌کالری و سالم."
                
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("خطا در ذخیره‌سازی BMI. لطفاً دوباره تلاش کنید.")
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
        return BMI_WEIGHT

# ... (rest of BMI-related functions) 