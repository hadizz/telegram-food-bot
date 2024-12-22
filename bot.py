from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler)
import handlers.recipe_handler as recipe_handler
from handlers.bmi_handler import *
from handlers.search_handler import *
from database.db_setup import init_db
from utils.common import cancel
from handlers.auth_handler import start_registration, register_username, ban_user_command, require_auth, REGISTER_USERNAME, show_profile
from handlers.recipe_handler import view_recipe_media
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get bot token from environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Recipe edit conversation handler
    edit_recipe_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(recipe_handler.start_recipe_edit, pattern="^edit_recipe_")
        ],
        states={
            recipe_handler.EDIT_WAITING: [
                CallbackQueryHandler(recipe_handler.handle_edit_selection, pattern="^edit_[0-9]+_")
            ],
            recipe_handler.EDIT_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recipe_handler.edit_title)
            ],
            recipe_handler.EDIT_INGREDIENTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recipe_handler.edit_ingredients)
            ],
            recipe_handler.EDIT_COOKING_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recipe_handler.edit_cooking_time)
            ],
            recipe_handler.EDIT_SKILL_LEVEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recipe_handler.edit_skill_level)
            ],
            recipe_handler.EDIT_CALORIES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recipe_handler.edit_calories)
            ],
            recipe_handler.EDIT_INSTRUCTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recipe_handler.edit_instructions)
            ],
            recipe_handler.EDIT_PHOTO: [
                MessageHandler(filters.PHOTO, recipe_handler.edit_photo),
                CommandHandler('skip', recipe_handler.skip_photo_edit)
            ],
            recipe_handler.EDIT_VOICE: [
                MessageHandler(filters.VOICE, recipe_handler.edit_voice),
                CommandHandler('skip', recipe_handler.skip_voice_edit)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(recipe_handler.handle_remove_media, pattern="^edit_[0-9]+_remove_")
        ],
        name="recipe_edit",
        persistent=False,
        per_message=False,
        per_chat=True,
        allow_reentry=True
    )
    
    # Add handlers in correct order
    app.add_handler(edit_recipe_handler)
    app.add_handler(CommandHandler("my_recipes", recipe_handler.show_my_recipes))
    app.add_handler(CallbackQueryHandler(recipe_handler.view_recipe_details, pattern="^view_recipe_"))
    
    # Registration conversation handler
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_registration)],
        states={
            REGISTER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_username)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(registration_handler)
    app.add_handler(CommandHandler("ban_user", ban_user_command))
    app.add_handler(CommandHandler("profile", show_profile))
    
    # Recipe addition conversation handler
    recipe_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_recipe', require_auth(recipe_handler.add_recipe_start))],
        states={
            recipe_handler.TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, require_auth(recipe_handler.receive_title))],
            recipe_handler.INGREDIENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, require_auth(recipe_handler.receive_ingredients))],
            recipe_handler.COOKING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, require_auth(recipe_handler.receive_cooking_time))],
            recipe_handler.SKILL_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, require_auth(recipe_handler.receive_skill_level))],
            recipe_handler.CALORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, require_auth(recipe_handler.receive_calories))],
            recipe_handler.INSTRUCTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, require_auth(recipe_handler.receive_instructions))],
            recipe_handler.INSTRUCTIONS_VOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, require_auth(recipe_handler.receive_instructions_voice))],
            recipe_handler.INSTRUCTIONS_VOICE_RECORD: [MessageHandler(filters.VOICE & ~filters.COMMAND, require_auth(recipe_handler.receive_instructions_voice_record))],
            recipe_handler.PHOTO: [MessageHandler(filters.PHOTO | filters.COMMAND, require_auth(recipe_handler.receive_photo))],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # BMI calculation conversation handler
    bmi_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('calculate_bmi', require_auth(calculate_bmi_start))],
        states={
            BMI_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, require_auth(receive_bmi_height))],
            BMI_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, require_auth(receive_bmi_weight))],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Search conversation handler
    search_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('search_recipes', require_auth(recipe_handler.search_recipes_start))],
        states={
            recipe_handler.SEARCH_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recipe_handler.search_recipes)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="search_recipes",
        persistent=False
    )
    
    app.add_handler(recipe_conv_handler)
    app.add_handler(bmi_conv_handler)
    app.add_handler(search_conv_handler)
    
    # # Debug middleware - moved to the end and modified filter
    # class DebugMiddleware:
    #     async def __call__(self, update, context, *args, **kwargs):
    #         if update.message and not update.message.text.startswith('/'):
    #             print(f"\n=== Debug Update ===")
    #             print(f"Update type: {update.message if update.message else update.callback_query}")
    #             print(f"Current state: {context.chat_data.get('recipe_edit', 'No state')}")
    #             print(f"User data: {context.user_data}")
    #             print("=============\n")
    #         return None
    
    # # Add debug middleware at the end with a more specific filter
    # app.add_handler(MessageHandler(
    #     filters.TEXT & ~filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
    #     DebugMiddleware()
    # ))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
