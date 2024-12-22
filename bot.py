from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler
import sqlite3
from datetime import datetime
import os

BOT_TOKEN = "your_bot_token_here"

# States for conversation handler
(TITLE, INGREDIENTS, COOKING_TIME, SKILL_LEVEL, CALORIES, 
 INSTRUCTIONS, PHOTO, BMI_HEIGHT, BMI_WEIGHT, SEARCH_QUERY) = range(10)

# Database setup
def init_db():
    conn = sqlite3.connect("recipes.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        ingredients TEXT NOT NULL,
        cooking_time INTEGER,
        skill_level TEXT,
        calories INTEGER,
        instructions TEXT NOT NULL,
        image_path TEXT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        bmi FLOAT,
        preferences TEXT
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        user_id INTEGER,
        recipe_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (recipe_id) REFERENCES recipes (id)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        recipe_id INTEGER,
        comment TEXT,
        created_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (recipe_id) REFERENCES recipes (id)
    )""")
    
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['/add_recipe', '/search_recipes'],
        ['/my_favorites', '/calculate_bmi'],
        ['/view_by_category', '/help']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Welcome to the Recipe Management System!\n\n"
        "🔹 Add new recipes\n"
        "🔹 Search by categories\n"
        "🔹 Calculate BMI and get personalized suggestions\n"
        "🔹 Save favorites\n"
        "🔹 Comment on recipes\n"
        "🔹 View cooking times and difficulty levels",
        reply_markup=reply_markup
    )

async def add_recipe_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter the recipe title:")
    return TITLE

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("Please enter the ingredients (comma-separated):")
    return INGREDIENTS

async def receive_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ingredients'] = update.message.text
    await update.message.reply_text("Enter cooking time (in minutes):")
    return COOKING_TIME

async def receive_cooking_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cooking_time'] = update.message.text
    keyboard = [['Beginner', 'Intermediate', 'Advanced']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Select skill level:", reply_markup=reply_markup)
    return SKILL_LEVEL

async def receive_skill_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['skill_level'] = update.message.text
    await update.message.reply_text("Enter calories (approximate number):")
    return CALORIES

async def receive_calories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['calories'] = update.message.text
    await update.message.reply_text("Enter cooking instructions (or send a voice message):")
    return INSTRUCTIONS

async def receive_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.voice:
        if not os.path.exists('voices'):
            os.makedirs('voices')
        
        voice = update.message.voice
        voice_path = f"voices/{voice.file_id}.ogg"
        file = await context.bot.get_file(voice.file_id)
        await file.download_to_drive(voice_path)
        context.user_data['instructions'] = voice_path
    else:
        context.user_data['instructions'] = update.message.text
    
    await update.message.reply_text("Send a photo of the dish (or /skip to skip):")
    return PHOTO

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '/skip':
        image_path = None
    else:
        if not os.path.exists('photos'):
            os.makedirs('photos')
        
        photo = update.message.photo[-1]
        print(photo)
        image_path = f"photos/{photo.file_id}.jpg"
        file = await context.bot.get_file(photo.file_id)
        await file.download_to_drive(image_path)
    # Save recipe to database
    try:
        conn = sqlite3.connect("recipes.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recipes (title, ingredients, cooking_time, skill_level, calories, 
                               instructions, image_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            context.user_data['title'],
            context.user_data['ingredients'],
            context.user_data['cooking_time'],
            context.user_data['skill_level'],
            context.user_data['calories'],
            context.user_data['instructions'],
            image_path
        ))
        conn.commit()
        conn.close()
        await update.message.reply_text("Recipe added successfully! 🎉")
    except Exception as e:
        await update.message.reply_text("Error saving recipe. Please try again.")
    
    return ConversationHandler.END

async def calculate_bmi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter your height in cm:")
    return BMI_HEIGHT

async def receive_bmi_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = float(update.message.text)
        context.user_data['height'] = height
        await update.message.reply_text("Please enter your weight in kg:")
        return BMI_WEIGHT
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return BMI_HEIGHT

async def receive_bmi_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text)
        height = context.user_data['height'] / 100  # convert cm to m
        bmi = weight / (height * height)
        
        # Save BMI to user profile
        conn = sqlite3.connect("recipes.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO users (telegram_id, bmi)
            VALUES (?, ?)
        """, (update.effective_user.id, bmi))
        conn.commit()
        conn.close()
        
        # Send BMI result and dietary suggestions
        message = f"Your BMI is: {bmi:.1f}\n\n"
        if bmi < 18.5:
            message += "Suggestion: Focus on high-protein and calorie-rich recipes."
        elif bmi < 25:
            message += "Suggestion: Maintain a balanced diet with varied recipes."
        else:
            message += "Suggestion: Focus on low-calorie and healthy recipes."
            
        await update.message.reply_text(message)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return BMI_WEIGHT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def search_recipes_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter a search term (recipe name or ingredient):")
    return SEARCH_QUERY

async def search_recipes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_term = update.message.text.lower()
    
    conn = sqlite3.connect("recipes.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, ingredients, cooking_time, skill_level, calories, image_path 
        FROM recipes 
        WHERE LOWER(title) LIKE ? OR LOWER(ingredients) LIKE ?
    """, (f'%{search_term}%', f'%{search_term}%'))
    
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        await update.message.reply_text("No recipes found matching your search.")
        return ConversationHandler.END
    
    for recipe in results:
        print(recipe)
        response = f"📝 {recipe[0]}\n"
        response += f"🥘 Ingredients: {recipe[1]}\n"
        response += f"⏱ Cooking time: {recipe[2]} minutes\n"
        response += f"📊 Skill level: {recipe[3]}\n"
        response += f"🔥 Calories: {recipe[4]}\n"
        
        # Send text first
        await update.message.reply_text(response)
        
        # Send photo if available
        if recipe[5]:  # image_path
            try:
                with open(recipe[5], 'rb') as photo:
                    await update.message.reply_photo(photo)
            except Exception as e:
                await update.message.reply_text("(Photo unavailable)")
        
        await update.message.reply_text("-------------------")
    
    return ConversationHandler.END

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Recipe addition conversation handler
    recipe_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_recipe', add_recipe_start)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
            INGREDIENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ingredients)],
            COOKING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_cooking_time)],
            SKILL_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_skill_level)],
            CALORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_calories)],
            INSTRUCTIONS: [MessageHandler(filters.TEXT | filters.VOICE & ~filters.COMMAND, receive_instructions)],
            PHOTO: [MessageHandler(filters.PHOTO | filters.COMMAND, receive_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # BMI calculation conversation handler
    bmi_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('calculate_bmi', calculate_bmi_start)],
        states={
            BMI_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bmi_height)],
            BMI_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bmi_weight)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Search conversation handler
    search_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('search_recipes', search_recipes_start)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_recipes)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(recipe_conv_handler)
    app.add_handler(bmi_conv_handler)
    app.add_handler(search_conv_handler)
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
