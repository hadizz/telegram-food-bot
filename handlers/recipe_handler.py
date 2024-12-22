from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes, ConversationHandler
import sqlite3
import os
from database.db_operations import DatabaseManager
from handlers.auth_handler import require_auth
import logging

# Initialize database manager
db = DatabaseManager()

# States for recipe conversation
(TITLE, INGREDIENTS, COOKING_TIME, SKILL_LEVEL, CALORIES, 
 INSTRUCTIONS, INSTRUCTIONS_VOICE, INSTRUCTIONS_VOICE_RECORD, PHOTO) = range(9)

# Add these states for editing
(EDIT_TITLE, EDIT_INGREDIENTS, EDIT_COOKING_TIME, 
 EDIT_SKILL_LEVEL, EDIT_CALORIES, EDIT_INSTRUCTIONS,
 EDIT_VOICE, EDIT_VOICE_RECORD, EDIT_PHOTO, EDIT_WAITING) = range(9, 19)

# Add search states
SEARCH_QUERY = 100

logger = logging.getLogger(__name__)

@require_auth
async def add_recipe_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لطفاً نام دستور پخت را وارد کنید:")
    return TITLE

@require_auth
async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("لطفاً مواد لازم را وارد کنید (با کاما جدا کنید):")
    return INGREDIENTS

async def receive_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ingredients'] = update.message.text
    await update.message.reply_text("زمان پخت را به دقیقه وارد کنید:")
    return COOKING_TIME

async def receive_cooking_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cooking_time'] = update.message.text
    keyboard = [['🟢 مبتدی', '🟡 متوسط', '🔴 حرفه‌ای']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("سطح دشواری را انتخاب کنید:", reply_markup=reply_markup)
    return SKILL_LEVEL

async def receive_skill_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['skill_level'] = update.message.text
    await update.message.reply_text("میزان کالری تقریبی را وارد کنید (فقط عدد):")
    return CALORIES

async def receive_calories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        calories = int(update.message.text)
        context.user_data['calories'] = calories
        await update.message.reply_text("دستور پخت را وارد کنید:")
        return INSTRUCTIONS
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید:")
        return CALORIES

async def receive_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['instructions'] = update.message.text
    keyboard = [['بله', 'خیر']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("آیا می‌خواهید دستور صوتی هم اضافه کنید؟", reply_markup=reply_markup)
    return INSTRUCTIONS_VOICE

async def receive_instructions_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == 'خیر':
        context.user_data['instruction_voice'] = None
        await update.message.reply_text("عکس غذا را ارسال کنید (یا /skip را بزنید):")
        return PHOTO
    elif update.message.text == 'بله':
        await update.message.reply_text("لطفاً پیام صوتی خود را ارسال کنید:")
        return INSTRUCTIONS_VOICE_RECORD

async def receive_instructions_voice_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.voice:
        if not os.path.exists('voices'):
            os.makedirs('voices')
        
        voice = update.message.voice
        voice_path = f"voices/{voice.file_id}.ogg"
        file = await context.bot.get_file(voice.file_id)
        await file.download_to_drive(voice_path)
        context.user_data['instruction_voice'] = voice_path
    
    await update.message.reply_text("عکس غذا را ارسال کنید (یا /skip را بزنید):")
    return PHOTO

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '/skip':
        image_path = None
    else:
        if not os.path.exists('photos'):
            os.makedirs('photos')
        
        photo = update.message.photo[-1]
        image_path = f"photos/{photo.file_id}.jpg"
        file = await context.bot.get_file(photo.file_id)
        await file.download_to_drive(image_path)
    
    recipe_data = {
        'title': context.user_data['title'],
        'ingredients': context.user_data['ingredients'],
        'cooking_time': context.user_data['cooking_time'],
        'skill_level': context.user_data['skill_level'],
        'calories': context.user_data['calories'],
        'instructions': context.user_data['instructions'],
        'instruction_voice': context.user_data.get('instruction_voice'),
        'image_path': image_path
    }
    
    if db.save_recipe(recipe_data, update.effective_user.id):
        await update.message.reply_text("دستور پخت با موفقیت ذخیره شد! 🎉")
    else:
        await update.message.reply_text("خطا در ذخیره‌سازی. لطفاً دوباره تلاش کنید.")
    
    return ConversationHandler.END

@require_auth
async def show_my_recipes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    recipes = db.get_user_recipes(user_id)
    
    if not recipes:
        await update.message.reply_text("شما هنوز دستور پختی ثبت نکرده‌اید! 🤔")
        return
    
    await update.message.reply_text("📚 لیست دستور پخت‌های شما:")
    
    for recipe in recipes:
        recipe_id, title, cooking_time, skill_level, calories, created_at = recipe
        
        # Create preview message
        message = (
            f"🍳 {title}\n"
            f"⏱ زمان پخت: {cooking_time} دقیقه\n"
            f"📊 سطح دشواری: {skill_level}\n"
            f"🔥 کالری: {calories}"
        )
        
        # Add view button
        keyboard = [[InlineKeyboardButton("👁 مشاهده کامل", callback_data=f"view_recipe_{recipe_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)

async def view_recipe_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        recipe_id = int(query.data.split('_')[2])
        recipe = db.get_recipe_details(recipe_id)
        
        if recipe:
            # Create message
            message = (
                f"🍳 {recipe['title']}\n\n"
                f"📝 مواد لازم:\n{recipe['ingredients']}\n\n"
                f"👨‍🍳 دستور پخت:\n{recipe['instructions']}\n\n"
                f"⏱ زمان پخت: {recipe['cooking_time']} دقیقه\n"
                f"📊 سطح دشواری: {recipe['skill_level']}\n"
                f"🔥 کالری: {recipe['calories']}\n"
                f"📅 تاریخ ثبت: {recipe['created_at']}"
            )
            
            # Only show edit button if user is the owner
            keyboard = []
            if recipe['owner_id'] == update.effective_user.id:
                keyboard.append([InlineKeyboardButton("✏️ ویرایش دستور", callback_data=f"edit_recipe_{recipe_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            await query.message.reply_text(
                message, 
                reply_markup=reply_markup
            )
            
            # Send photo if available
            if recipe['image_path']:
                try:
                    with open(recipe['image_path'], 'rb') as photo:
                        await query.message.reply_photo(photo)
                except Exception as e:
                    await query.message.reply_text("(تصویر در دسترس نیست)")
            
            # Send voice instruction if available
            if recipe['instruction_voice']:
                try:
                    with open(recipe['instruction_voice'], 'rb') as voice:
                        await query.message.reply_voice(voice)
                except Exception as e:
                    await query.message.reply_text("(فایل صوتی در دسترس نیست)")
        else:
            await query.message.reply_text("متأسفانه این دستور پخت یافت نشد.")
            
    except Exception as e:
        print(f"Error in view_recipe_details: {e}")
        await query.message.reply_text("خطا در نمایش اطلاعات. لطفاً دوباره تلاش کنید.")

@require_auth
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    user_id = update.inline_query.from_user.id
    
    results = []
    
    # Check if it's a full recipe request
    if query.startswith('receipt_full:'):
        try:
            recipe_id = int(query.split(':')[1])
            recipe = db.get_recipe_details(recipe_id)
            
            if recipe:
                full_content = (
                    f"🍳 {recipe['title']}\n\n"
                    f"📝 مواد لازم:\n{recipe['ingredients']}\n\n"
                    f"👨‍🍳 دستور پخت:\n{recipe['instructions']}\n\n"
                    f"⏱ زمان پخت: {recipe['cooking_time']} دقیقه\n"
                    f"📊 سطح دشواری: {recipe['skill_level']}\n"
                    f"🔥 کالری: {recipe['calories']}\n"
                    f"📅 تاریخ ثبت: {recipe['created_at']}"
                )
                
                results.append(
                    InlineQueryResultArticle(
                        id=str(recipe_id),
                        title=f"دستور امل: {recipe['title']}",
                        description="برای مشاهده کامل کلیک کنید",
                        input_message_content=InputTextMessageContent(
                            message_text=full_content,
                            parse_mode='HTML'
                        ),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("📸 مشاهده تصویر و صوت", callback_data=f"view_media_{recipe_id}")
                        ]])
                    )
                )
        except (ValueError, IndexError):
            pass
    else:
        # Regular recipe list
        recipes = db.get_user_recipes(user_id)
        for recipe in recipes:
            recipe_id, title, cooking_time, skill_level, calories, created_at = recipe
            
            if not query or query.lower() in title.lower():
                preview_content = (
                    f"🍳 {title}\n"
                    f"⏱ زمان پخت: {cooking_time} دقیقه\n"
                    f"📊 سطح دشواری: {skill_level}\n"
                    f"🔥 کالری: {calories}"
                )
                
                results.append(
                    InlineQueryResultArticle(
                        id=str(recipe_id),
                        title=title,
                        description=f"زمان پخت: {cooking_time} دقیقه | کالری: {calories}",
                        input_message_content=InputTextMessageContent(
                            message_text=preview_content,
                            parse_mode='HTML'
                        ),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("مشاهده کامل", 
                                               switch_inline_query_current_chat=f"receipt_full:{recipe_id}")
                        ]])
                    )
                )
    
    await update.inline_query.answer(results)

# Add new handler for media viewing
async def view_recipe_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print('view_recipe_media', update)
        query = update.callback_query
        await query.answer()
        
        recipe_id = int(query.data.split('_')[2])
        recipe = db.get_recipe_details(recipe_id)
        
        print('retrive recipe', recipe)
        # Use query.chat_instance instead of query.message.chat.id
        chat_id = query.chat_instance
        print('chat_id', chat_id)
        if recipe and chat_id:
            # Send photo if available
            if recipe['image_path']:
                try:
                    with open(recipe['image_path'], 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo
                        )
                except Exception as e:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="(تصویر در دسترس نیست)"
                    )
            
            # Send voice instruction if available
            if recipe['instruction_voice']:
                try:
                    with open(recipe['instruction_voice'], 'rb') as voice:
                        await context.bot.send_voice(
                            chat_id=chat_id,
                            voice=voice
                        )
                except Exception as e:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="(فایل صوتی در دسترس نیست)"
                    )
    except Exception as e:
        print(f"Error in view_recipe_media: {e}")
        if query.message and query.message.chat:
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text="خطا در نمایش رسانه‌ها. لطفاً دوباره تلاش کنید."
            )

async def start_recipe_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("\n=== Starting Recipe Edit ===")
    query = update.callback_query
    await query.answer()
    print('query.data', query.data)
    recipe_id = int(query.data.split('_')[2])
    recipe = db.get_recipe_details(recipe_id)
    print(f"Recipe ID: {recipe_id}")
    print(f"Recipe data: {recipe}")
    
    if recipe:
        context.user_data['editing_recipe_id'] = recipe_id
        context.user_data['original_recipe'] = recipe
        print(f"Stored in context: {context.user_data}")
        
        keyboard = [
            [InlineKeyboardButton("عنوان", callback_data=f"edit_{recipe_id}_title"),
             InlineKeyboardButton("مواد لازم", callback_data=f"edit_{recipe_id}_ingredients")],
            [InlineKeyboardButton("زمان پخت", callback_data=f"edit_{recipe_id}_time"),
             InlineKeyboardButton("سطح دشواری", callback_data=f"edit_{recipe_id}_level")],
            [InlineKeyboardButton("کالری", callback_data=f"edit_{recipe_id}_calories"),
             InlineKeyboardButton("دستور پخت", callback_data=f"edit_{recipe_id}_instructions")],
        ]
        
        # Add photo buttons if photo exists
        if recipe.get('image_path'):
            keyboard.append([
                InlineKeyboardButton("🔄 تغییر عکس", callback_data=f"edit_{recipe_id}_photo"),
                InlineKeyboardButton("❌ حذف عکس", callback_data=f"edit_{recipe_id}_remove_photo")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("➕ افزودن عکس", callback_data=f"edit_{recipe_id}_photo")
            ])
        
        # Add voice buttons if voice exists
        if recipe.get('instruction_voice'):
            keyboard.append([
                InlineKeyboardButton("🔄 تغییر صدا", callback_data=f"edit_{recipe_id}_voice"),
                InlineKeyboardButton("❌ حذف صدا", callback_data=f"edit_{recipe_id}_remove_voice")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("➕ افزودن صدا", callback_data=f"edit_{recipe_id}_voice")
            ])
            
        keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data=f"edit_{recipe_id}_cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "چه بخشی از دستور پخت را می‌خواهید ویرایش کنید؟",
            reply_markup=reply_markup
        )
        print("Returning to WAITING state")
        return EDIT_WAITING
    print("Recipe not found, ending conversation")
    return ConversationHandler.END

async def handle_edit_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("\n=== Handling Edit Selection ===")
    query = update.callback_query
    await query.answer()
    
    # Parse the callback data: edit_<recipe_id>_<field>
    parts = query.data.split('_')
    recipe_id = int(parts[1])
    selection = '_'.join(parts[2:])  # Join remaining parts to handle 'remove_photo' and 'remove_voice'
    print(f"Edit selection: recipe_id={recipe_id}, selection={selection}")
    
    if selection == 'cancel':
        await query.message.reply_text("ویرایش لغو شد.")
        print("Edit cancelled")
        return ConversationHandler.END
        
    if selection in ['remove_photo', 'remove_voice']:
        try:
            recipe = db.get_recipe_details(recipe_id)
            if not recipe:
                await query.message.reply_text("خطا در دریافت اطلاعات دستور پخت.")
                return ConversationHandler.END
            
            if selection == 'remove_photo':
                if recipe.get('image_path') and os.path.exists(recipe['image_path']):
                    os.remove(recipe['image_path'])
                recipe['image_path'] = None
                success_message = "عکس با موفقیت حذف شد! ✅"
            else:  # remove_voice
                if recipe.get('instruction_voice') and os.path.exists(recipe['instruction_voice']):
                    os.remove(recipe['instruction_voice'])
                recipe['instruction_voice'] = None
                success_message = "صدا با موفقیت حذف شد! ✅"
            
            if db.update_recipe(recipe_id, update.effective_user.id, recipe):
                await query.message.reply_text(success_message)
            else:
                await query.message.reply_text("خطا در حذف. لطفاً دوباره تلاش کنید.")
        except Exception as e:
            print(f"Error removing media: {e}")
            await query.message.reply_text("خطا در حذف. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END
    
    # Store recipe_id in context
    context.user_data['editing_recipe_id'] = recipe_id
    recipe = db.get_recipe_details(recipe_id)
    if not recipe:
        await query.message.reply_text("خطا در دریافت اطلاعات دستور پخت.")
        print(f"Recipe {recipe_id} not found")
        return ConversationHandler.END
        
    context.user_data['original_recipe'] = recipe
    print(f"Stored recipe in context: {recipe}")
    
    prompts = {
        'title': "عنوان جدید را وارد کنید:",
        'ingredients': "مواد لازم جدید را وارد کنید (با کاما جدا کنید):",
        'time': "زمان پخت جدید را به دقیقه وارد کنید:",
        'level': "سطح دشواری جدید را انتخاب کنید:",
        'calories': "کالری جدید را وارد کنید:",
        'instructions': "دستور پخت جدید را وارد کنید:",
        'photo': "عکس جدید را ارسال کنید (یا /skip برای انصراف):",
        'voice': "صدای جدید را ارسال کنید (یا /skip برای انصراف):"
    }
    
    state_map = {
        'title': EDIT_TITLE,
        'ingredients': EDIT_INGREDIENTS,
        'time': EDIT_COOKING_TIME,
        'level': EDIT_SKILL_LEVEL,
        'calories': EDIT_CALORIES,
        'instructions': EDIT_INSTRUCTIONS,
        'photo': EDIT_PHOTO,
        'voice': EDIT_VOICE
    }
    
    next_state = state_map.get(selection)
    print(f"Next state: {next_state}")
    
    if next_state is None:
        await query.message.reply_text("گزینه نامعتبر.")
        print(f"Invalid selection: {selection}")
        return ConversationHandler.END
    
    if selection == 'level':
        keyboard = [['مبتدی', 'متوسط', 'حرفه‌ای']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await query.message.reply_text(prompts[selection], reply_markup=reply_markup)
    else:
        await query.message.reply_text(prompts[selection])
    
    # Store the current edit state and recipe data in context
    context.chat_data['recipe_edit'] = next_state
    context.chat_data['editing_recipe_id'] = recipe_id
    context.chat_data['original_recipe'] = recipe
    print(f"Transitioning to state: {next_state}")
    return next_state

# Add these handlers after handle_edit_selection

async def show_edit_menu(recipe_id: int, message) -> int:
    """Helper function to show the edit menu"""
    recipe = db.get_recipe_details(recipe_id)
    if not recipe:
        await message.reply_text("خطا در دریافت اطلاعات دستور پخت.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("عنوان", callback_data=f"edit_{recipe_id}_title"),
         InlineKeyboardButton("مواد لازم", callback_data=f"edit_{recipe_id}_ingredients")],
        [InlineKeyboardButton("زمان پخت", callback_data=f"edit_{recipe_id}_time"),
         InlineKeyboardButton("سطح دشواری", callback_data=f"edit_{recipe_id}_level")],
        [InlineKeyboardButton("کالری", callback_data=f"edit_{recipe_id}_calories"),
         InlineKeyboardButton("دستور پخت", callback_data=f"edit_{recipe_id}_instructions")],
    ]
    
    # Add photo buttons if photo exists
    if recipe.get('image_path'):
        keyboard.append([
            InlineKeyboardButton("🔄 تغییر عکس", callback_data=f"edit_{recipe_id}_photo"),
            InlineKeyboardButton("❌ حذف عکس", callback_data=f"edit_{recipe_id}_remove_photo")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("➕ افزودن عکس", callback_data=f"edit_{recipe_id}_photo")
        ])
    
    # Add voice buttons if voice exists
    if recipe.get('instruction_voice'):
        keyboard.append([
            InlineKeyboardButton("🔄 تغییر صدا", callback_data=f"edit_{recipe_id}_voice"),
            InlineKeyboardButton("❌ حذف صدا", callback_data=f"edit_{recipe_id}_remove_voice")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("➕ افزودن صدا", callback_data=f"edit_{recipe_id}_voice")
        ])
        
    keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data=f"edit_{recipe_id}_cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "چه بخشی از دستور پخت را می‌خواهید ویرایش کنید؟",
        reply_markup=reply_markup
    )
    return EDIT_WAITING

async def edit_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipe_id = context.user_data.get('editing_recipe_id')
    recipe = context.user_data.get('original_recipe')
    
    if not recipe or not recipe_id:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END
    
    recipe['title'] = update.message.text
    
    if db.update_recipe(recipe_id, update.effective_user.id, recipe):
        await update.message.reply_text("عنوان با موفقیت ویرایش شد! ✅")
        return await show_edit_menu(recipe_id, update.message)
    else:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END

async def edit_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipe_id = context.user_data.get('editing_recipe_id')
    recipe = context.user_data.get('original_recipe')
    
    if not recipe or not recipe_id:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END
    
    recipe['ingredients'] = update.message.text
    
    if db.update_recipe(recipe_id, update.effective_user.id, recipe):
        await update.message.reply_text("مواد لازم با موفقیت ویرایش شد! ✅")
        return await show_edit_menu(recipe_id, update.message)
    else:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END

async def edit_cooking_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipe_id = context.user_data.get('editing_recipe_id') or context.chat_data.get('editing_recipe_id')
    recipe = context.user_data.get('original_recipe') or context.chat_data.get('original_recipe')
    
    if not recipe or not recipe_id:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END
    
    try:
        new_time = update.message.text.strip()
        
        # Validate the input
        if not new_time.isdigit():
            await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
            return EDIT_COOKING_TIME
            
        recipe['cooking_time'] = new_time
        
        if db.update_recipe(recipe_id, update.effective_user.id, recipe):
            await update.message.reply_text("زمان پخت با موفقیت ویرایش شد! ✅")
            return await show_edit_menu(recipe_id, update.message)
        else:
            await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
    except Exception as e:
        print(f"Error updating recipe: {e}")
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
    
    return ConversationHandler.END

async def edit_skill_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipe_id = context.user_data.get('editing_recipe_id')
    recipe = context.user_data.get('original_recipe')
    
    if not recipe or not recipe_id:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END
    
    recipe['skill_level'] = update.message.text
    
    if db.update_recipe(recipe_id, update.effective_user.id, recipe):
        await update.message.reply_text("سطح دشواری با موفقیت ویرایش شد! ✅")
        return await show_edit_menu(recipe_id, update.message)
    else:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END

async def edit_calories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipe_id = context.user_data.get('editing_recipe_id')
    recipe = context.user_data.get('original_recipe')
    
    if not recipe or not recipe_id:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END
    
    try:
        calories = int(update.message.text)
        recipe['calories'] = calories
        
        if db.update_recipe(recipe_id, update.effective_user.id, recipe):
            await update.message.reply_text("کالری با موفقیت ویرایش شد! ✅")
            return await show_edit_menu(recipe_id, update.message)
        else:
            await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
        return EDIT_CALORIES
    
    return ConversationHandler.END

async def edit_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipe_id = context.user_data.get('editing_recipe_id')
    recipe = context.user_data.get('original_recipe')
    
    if not recipe or not recipe_id:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END
    
    recipe['instructions'] = update.message.text
    
    if db.update_recipe(recipe_id, update.effective_user.id, recipe):
        await update.message.reply_text("دستور پخت با موفقیت ویرایش شد! ✅")
        return await show_edit_menu(recipe_id, update.message)
    else:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END

async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipe_id = context.user_data.get('editing_recipe_id') or context.chat_data.get('editing_recipe_id')
    recipe = context.user_data.get('original_recipe') or context.chat_data.get('original_recipe')
    
    if not recipe or not recipe_id:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END
    
    try:
        if not os.path.exists('photos'):
            os.makedirs('photos')
        
        # Remove old photo if exists
        if recipe.get('image_path') and os.path.exists(recipe['image_path']):
            os.remove(recipe['image_path'])
        
        photo = update.message.photo[-1]
        image_path = f"photos/{photo.file_id}.jpg"
        file = await context.bot.get_file(photo.file_id)
        await file.download_to_drive(image_path)
        
        recipe['image_path'] = image_path
        
        if db.update_recipe(recipe_id, update.effective_user.id, recipe):
            await update.message.reply_text("عکس با موفقیت ویرایش شد! ✅")
            return await show_edit_menu(recipe_id, update.message)
        else:
            await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
    except Exception as e:
        print(f"Error updating photo: {e}")
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
    
    return ConversationHandler.END

async def edit_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipe_id = context.user_data.get('editing_recipe_id') or context.chat_data.get('editing_recipe_id')
    recipe = context.user_data.get('original_recipe') or context.chat_data.get('original_recipe')
    
    if not recipe or not recipe_id:
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END
    
    try:
        if not os.path.exists('voices'):
            os.makedirs('voices')
        
        # Remove old voice if exists
        if recipe.get('instruction_voice') and os.path.exists(recipe['instruction_voice']):
            os.remove(recipe['instruction_voice'])
        
        voice = update.message.voice
        voice_path = f"voices/{voice.file_id}.ogg"
        file = await context.bot.get_file(voice.file_id)
        await file.download_to_drive(voice_path)
        
        recipe['instruction_voice'] = voice_path
        
        if db.update_recipe(recipe_id, update.effective_user.id, recipe):
            await update.message.reply_text("صدا با موفقیت ویرایش شد! ✅")
            return await show_edit_menu(recipe_id, update.message)
        else:
            await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
    except Exception as e:
        print(f"Error updating voice: {e}")
        await update.message.reply_text("خطا در ویرایش. لطفاً دوباره تلاش کنید.")
    
    return ConversationHandler.END

async def skip_photo_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ویرایش عکس لغو شد.")
    return ConversationHandler.END

async def skip_voice_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ویرایش صدا لغو شد.")
    return ConversationHandler.END

async def handle_remove_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    recipe_id = int(parts[1])
    media_type = parts[3]  # 'photo' or 'voice'
    
    recipe = db.get_recipe_details(recipe_id)
    if not recipe:
        await query.message.reply_text("خطا در دریافت اطلاعات دستور پخت.")
        return ConversationHandler.END
    
    try:
        if media_type == 'photo':
            if recipe.get('image_path') and os.path.exists(recipe['image_path']):
                os.remove(recipe['image_path'])
            recipe['image_path'] = None
            success_message = "عکس با موفقیت حذف شد! ✅"
        else:  # voice
            if recipe.get('instruction_voice') and os.path.exists(recipe['instruction_voice']):
                os.remove(recipe['instruction_voice'])
            recipe['instruction_voice'] = None
            success_message = "صدا با موفقیت حذف شد! ✅"
        
        if db.update_recipe(recipe_id, update.effective_user.id, recipe):
            await query.message.reply_text(success_message)
            return await show_edit_menu(recipe_id, query.message)
        else:
            await query.message.reply_text("خطا در حذف. لطفاً دوباره تلاش کنید.")
    except Exception as e:
        print(f"Error removing media: {e}")
        await query.message.reply_text("خطا در حذف. لطفاً دوباره تلاش کنید.")
    
    return ConversationHandler.END

@require_auth
async def search_recipes_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 جستجو در دستور پخت‌ها\n\n"
        "لطفاً عبارت مورد نظر خود را وارد کنید. می‌توانید در:\n"
        "- نام غذا\n"
        "- مواد لازم\n"
        "- دستور پخت\n"
        "جستجو کنید."
    )
    return SEARCH_QUERY

async def search_recipes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_term = update.message.text
    if len(search_term) < 2:
        await update.message.reply_text("لطفاً حداقل ۲ حرف وارد کنید.")
        return SEARCH_QUERY
    
    results = db.search_recipes(search_term)
    
    if not results:
        await update.message.reply_text(
            "🔍 نتیجه‌ای یافت نشد!\n"
            "می‌توانید با عبارت دیگری جستجو کنید یا از /cancel برای خروج استفاده کنید."
        )
        return SEARCH_QUERY
    
    await update.message.reply_text(f"🔍 {len(results)} نتیجه یافت شد:")
    
    for result in results:
        recipe_id, title, ingredients, cooking_time, skill_level, calories, image_path, owner_id, owner_username = result
        
        # Create preview message
        message = (
            f"🍳 {title}\n"
            f"👨‍🍳 آشپز: {owner_username or 'ناشناس'}\n"
            f"⏱ زمان پخت: {cooking_time} دقیقه\n"
            f"📊 سطح دشواری: {skill_level}\n"
            f"🔥 کالری: {calories}\n\n"
            f"📝 مواد لازم:\n{ingredients[:100]}..."  # Show first 100 chars of ingredients
        )
        
        # Add view button
        keyboard = [[InlineKeyboardButton("👁 مشاهده کامل", callback_data=f"view_recipe_{recipe_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send message with photo if available
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=message,
                        reply_markup=reply_markup
                    )
            except Exception as e:
                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup
            )
    
    await update.message.reply_text(
        "می‌توانید عبارت جدیدی جستجو کنید یا از /cancel برای خروج استفاده کنید."
    )
    return SEARCH_QUERY

# ... (rest of recipe-related functions) 