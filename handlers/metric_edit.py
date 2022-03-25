from telegram.ext import (
    CallbackContext, 
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
)
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ReplyKeyboardRemove,
    ParseMode
)

import logging

from db_utils import YDataBase
from utils import upload_photo, dev_ids

logger = logging.getLogger(__name__)

PRINT_INFO, CHOOSE, CHECK = range(3)

reply_keyboard = [["отмена"]]

steps = {
    0: {
        "field": "name",
        "msg": "Придумай название для показателя",
        "reply_keyboard": reply_keyboard,
        "func": lambda x: x.text
    },
    1: {
        "field": "scale",
        "msg": "В каком диапазоне измеряется показатель? Пришли 2 числа, например:\n-100 100\n6 50",
        "reply_keyboard": reply_keyboard,
        "func": lambda x: [int(val) for val in x.text.split(" ")]
    },
    2: {
        "field": "template",
        "msg": ("Пришли шаблон для текста. В шаблоне можно использовать спец. слова, которые будут заменяться на конкретные. Можно использовать смайлики"
        +"\nСпец слова:\n"
        +"\n".join(
            [
                "- <code>{value}</code> - значение показателя",
                # "- <code>{unit}</code> - единица измерения",
                "- <code>{first_name}</code> - имя того, кто спрашивает",
                "- <code>{last_name}</code> - фамилия"
            ])
        +"\n\nНапример:\nваша ауфность {value}%. Ауф! 🐺"
        ),

        "reply_keyboard": reply_keyboard,
        "parse_mode": ParseMode.HTML,
        "func": lambda x: x.text
    },
    3: {
        "field": "img_url",
        "msg": "Пришли пикчу или ссылку - она будет отображаться в списке того, что можно измерять. Можешь пропустить",
        "reply_keyboard": [["отмена", "пропустить"]],
        "func": lambda x: None if x.text=="пропустить" else upload_photo(x)
    },
    4: {
        "field": "check",
        "msg": "Проверь что всё верно",
        "reply_keyboard": [["отмена", "всё ок"]],
        "func": lambda x: None if x=="пропустить" else x,
        "add": False,
        "msg_func": True
    }, 
}

def edit_metric_enter(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    context.user_data["metric"] = YDataBase().fetch_last_config(user_id=None if user_id in dev_ids else user_id)
    metrics = context.user_data["metric"]
    if metrics:
        keyboard = [
            [InlineKeyboardButton(metrics["name"], callback_data=metrics["name"])]
            for m in metrics
        ] + [[InlineKeyboardButton("отмена", callback_data="end")]]

        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "Какой индикатор изменить?",
            reply_markup=reply_markup
        )
        return PRINT_INFO
    
    else:
        update.message.reply_text(
            "Вы ещё не добавили никаких индикаторов!",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


def show_selected_metric(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    metric_selected_ls = [m for m in context.user_data["metric"] if m["name"]==query]
    if metric_selected_ls:
        metric_selected = metric_selected_ls[0]
        context.user_data["metric_selected"] = metric_selected
        text = "Название: {name}\nДиапазон: {scale_low}...{scale_high}\nШаблон: {template}\n".format(**metric_selected)
        keyboard = [
            [InlineKeyboardButton("Удалить", callback_data="delete")],
            [InlineKeyboardButton("<", callback_data="back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text,
            reply_markup=reply_markup
        )
        return CHOOSE


def delete_selected_metric(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    metric_selected = context.user_data["metric_selected"]
    try:
        update.message.reply_text(
            "Индикатор успешно удалён!"
        )
        result = YDataBase().execute_query("DELETE FROM measures WHERE id={id}".format(**metric_selected))
        user_id = update.effective_user.id
        context.user_data["metric"] = YDataBase().fetch_last_config(user_id=None if user_id in dev_ids else user_id)
        metrics = context.user_data["metric"]
        if metrics:
            keyboard = [
                [InlineKeyboardButton(metrics["name"], callback_data=metrics["name"])]
                for m in metrics
            ] + [[InlineKeyboardButton("отмена", callback_data="end")]]

            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(
                "Какой индикатор изменить?",
                reply_markup=reply_markup
            )
            return PRINT_INFO
        else:
            update.message.reply_text(
                "Вы ещё не добавили никаких индикаторов!",
                reply_markup=ReplyKeyboardRemove()
            )

    except Exception as e:
        logger.exception("Error deleting metric")
        update.message.reply_text(
            "Что-то пошло не так",
            reply_markup=ReplyKeyboardRemove()
        )
    return ConversationHandler.END


def edit_metric_final(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Не очень-то и хотелось.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


edit_metric_handl = ConversationHandler(
    entry_points=[CommandHandler('edit_metric', edit_metric_enter)],
    states={
        PRINT_INFO: [CallbackQueryHandler(show_selected_metric, pattern=r'\w*')],
        CHOOSE: [
            CallbackQueryHandler(delete_selected_metric, pattern=r'^delete$'),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(edit_metric_final, pattern=r'^end$'),
    ],
    persistent=True,
    name='add_metric_handler'
)