from .user import register_user_handlers
from .moderation import register_moderation_handlers
from .admin import register_admin_handlers

def register_handlers(dp, bot):
    register_user_handlers(dp, bot)
    register_moderation_handlers(dp, bot)
    register_admin_handlers(dp, bot)