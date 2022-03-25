from telegram.ext import (
    Updater, 
    CallbackContext, 
    InlineQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Filters
)
from telegram import (
    Bot,
    InlineQueryResultArticle, 
    InputTextMessageContent, 
    Update,
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove,
    ParseMode
)

import logging
import yaml
import arrow
import os

from db_utils import YDataBase
from ydb_persistence import YDBPersistence
from utils import upload_photo, create_text


GET_PARAM, SET_PARAM, CHECK = range(3)

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

def add_metric_enter(update: Update, context: CallbackContext) -> int:
    context.user_data["metric"] = {
        "id": arrow.utcnow().int_timestamp,
        "creator_id": update.effective_user.id,
        "volatile_level": 1
    }
    context.user_data["step"] = 0
    step = context.user_data["step"]
    step_params = steps[step]
    reply_markup = ReplyKeyboardMarkup(
        step_params["reply_keyboard"], 
        one_time_keyboard=True, 
        resize_keyboard=True
    )
    update.message.reply_text(
        step_params["msg"],
        reply_markup=reply_markup,
        parse_mode=step_params.get("parse_mode")
    )
    return SET_PARAM


def add_metric_set_param(update: Update, context: CallbackContext) -> int:
    metric = context.user_data["metric"]
    step = context.user_data["step"]
    step_params = steps[step]
    if update.message.text or update.message.photo and step_params.get("add", True):
        if step_params["field"]=="scale":
            metric["{field}_low".format(**step_params)], metric["{field}_high".format(**step_params)] = step_params.get("func", lambda x: x.text)(update.message)
        else:
            metric[step_params["field"]] = step_params.get("func", lambda x: x.text)(update.message)
    context.user_data["step"] += 1
    try:
        step_params = steps[step+1]
    except:
        pass
    reply_markup = ReplyKeyboardMarkup(
        step_params["reply_keyboard"], 
        one_time_keyboard=True, 
        resize_keyboard=True
    )
    txt = step_params["msg"]
    if step_params.get("msg_func"):
        txt += "\n" + create_text(
            user_id=update.effective_user.id, 
            first_name=update.effective_user.first_name,
            last_name=update.effective_user.last_name,
            query="",
            params=metric
        )
    update.message.reply_text(
        txt,
        reply_markup=reply_markup,
        parse_mode=step_params.get("parse_mode")
    )
    return SET_PARAM


def add_metric_final(update: Update, context: CallbackContext) -> int:
    metric = context.user_data["metric"]
    result = YDataBase().execute_query(
        query='''UPSERT INTO measures (id, creator_id, name, scale_high, scale_low, template, volatile_level, img_url) 
        VALUES ({id}, {creator_id}, "{name}", {scale_high}, {scale_low}, "{template}", {volatile_level}, "{img_url}")'''.format(
            **metric
        )
    )
    update.message.reply_text(
        "Поздравляю! Ты заделал_а новый показатель - {name}".format(**metric),
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def add_metric_end(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Не очень-то и хотелось.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


add_metric_handl = ConversationHandler(
    entry_points=[CommandHandler('add_metric', add_metric_enter)],
    states={
        SET_PARAM: [MessageHandler(~(Filters.regex('^всё ок$')|Filters.regex('^отмена$')), add_metric_set_param)],
        CHECK: [MessageHandler(~(Filters.regex('^всё ок$')|Filters.regex('^отмена$')), add_metric_final)],
    },
    fallbacks=[
        MessageHandler(Filters.regex('^отмена$'), add_metric_end),
        MessageHandler(Filters.regex('^всё ок$'), add_metric_final)
    ],
    persistent=True,
    name='add_metric_handler'
)