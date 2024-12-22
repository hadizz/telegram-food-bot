from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database.db_operations import DatabaseManager

# States for registration
(REGISTER_USERNAME) = range(1)

db = DatabaseManager()

def require_auth(func):
    """Decorator to check if user is registered and not banned"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not db.is_user_registered(user_id):
            await update.message.reply_text(
                "شما هنوز ثبت نام نکرده‌اید. لطفا ابتدا با دستور /start ثبت نام کنید."
            )
            return ConversationHandler.END
            
        return await func(update, context, *args, **kwargs)
    return wrapper

def admin_only(func):
    """Decorator to check if user is super admin"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not db.is_super_admin(user_id):
            await update.message.reply_text("شما دسترسی به این بخش را ندارید.")
            return ConversationHandler.END
            
        return await func(update, context, *args, **kwargs)
    return wrapper

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if db.is_user_registered(user.id):
        keyboard = [
            ['/add_recipe', '/my_recipes'],
            ['/search_recipes', '/calculate_bmi'],
            ['/my_favorites', '/profile'],
            ['/help']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"خوش آمدید {user.full_name} عزیز 👋\n\n"
            "از منوی زیر می‌توانید استفاده کنید:",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "سلام به سیستم مدیریت دستور پخت خوش آمدید!\n\n"
        "لطفاً نام کاربری خود را وارد کنید:"
    )
    context.user_data['telegram_id'] = user.id
    context.user_data['full_name'] = user.full_name
    return REGISTER_USERNAME

async def register_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    telegram_id = context.user_data['telegram_id']
    full_name = context.user_data['full_name']
    
    success = db.register_user(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name
    )
    
    if success:
        keyboard = [
            ['/add_recipe', '/my_recipes'],
            ['/search_recipes', '/calculate_bmi'],
            ['/my_favorites', '/profile'],
            ['/help']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"ثبت نام شما با موفقیت انجام شد!\n"
            f"خوش آمدید {full_name} عزیز 👋\n\n"
            "از منوی زیر می‌توانید استفاده کنید:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("متأسفانه در ثبت نام مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")
    
    return ConversationHandler.END

# Admin commands
@admin_only
async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("لطفاً شناسه کاربری را وارد کنید.")
        return
    
    user_id = int(context.args[0])
    if db.ban_user(user_id):
        await update.message.reply_text("کاربر با موفقیت مسدود شد.")
    else:
        await update.message.reply_text("خطا در مسدود کردن کاربر.") 

@require_auth
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = db.get_user_profile(user_id)
    
    if profile:
        status = "فعال ✅" if profile['is_active'] else "غیرفعال ❌"
        message = (
            "📋 اطلاعات پروفایل شما:\n\n"
            f"👤 نام: {profile['full_name']}\n"
            f"🔖 نام کاربری: {profile['username']}\n"
            f"📅 تاریخ عضویت: {profile['joined_date']}\n"
            f"📊 وضعیت: {status}"
        )
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("خطا در دریافت اطلاعات پروفایل.") 