from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database.db_operations import DatabaseManager

# Initialize database manager
db = DatabaseManager()

# States for search conversation
SEARCH_QUERY = 0

async def search_recipes_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عبارت جستجو را وارد کنید (نام غذا یا مواد لازم):")
    return SEARCH_QUERY

async def search_recipes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_term = update.message.text
    results = db.search_recipes(search_term)
    
    if not results:
        await update.message.reply_text("هیچ دستور پختی یافت نشد.")
        return ConversationHandler.END
    
    for recipe in results:
        response = f"📝 نام غذا: {recipe[0]}\n"
        response += f"🥘 مواد لازم: {recipe[1]}\n"
        response += f"⏱ زمان پخت: {recipe[2]} دقیقه\n"
        response += f"📊 سطح دشواری: {recipe[3]}\n"
        response += f"🔥 کالری: {recipe[4]}\n"
        
        await update.message.reply_text(response)
        
        if recipe[5]:  # image_path
            try:
                with open(recipe[5], 'rb') as photo:
                    await update.message.reply_photo(photo)
            except Exception as e:
                await update.message.reply_text("(تصویر در دسترس نیست)")
        
        await update.message.reply_text("-------------------")
    
    return ConversationHandler.END

# ... (rest of search-related functions) 