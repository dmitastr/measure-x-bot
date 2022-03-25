from telegram.ext import (
    CallbackContext, 
    CommandHandler
)
from telegram import (
    Update
)

from db_utils import YDataBase
from utils import dev_ids


def start(update: Update, context: CallbackContext) -> None:
    if update.message.chat.id in dev_ids:
        update.message.reply_text("Ауф")


def update_config_first(context: CallbackContext) -> None:
    context.bot_data["config"] = YDataBase().fetch_last_config()


start_handl = CommandHandler("start", start)