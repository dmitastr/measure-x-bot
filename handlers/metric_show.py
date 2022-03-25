from telegram.ext import (
    CallbackContext, 
    InlineQueryHandler
)
from telegram import (
    InlineQueryResultArticle, 
    InputTextMessageContent, 
    Update
)

import logging

from db_utils import YDataBase
from utils import create_text

logger = logging.getLogger(__name__)


def metric_show(update: Update, context: CallbackContext) -> None:
    metrics = YDataBase().fetch_last_config()
    user_id = update.inline_query.from_user.id
    first_name = update.inline_query.from_user.first_name
    last_name = update.inline_query.from_user.last_name
    query = update.inline_query.query or ""
    results = [
        InlineQueryResultArticle(
            id=metric["id"],
            title="Покажи {name}!".format(**metric),
            input_message_content=InputTextMessageContent(
                message_text=create_text(
                    user_id=user_id, 
                    first_name=first_name,
                    last_name=last_name,
                    query=query,
                    params=metric
                )
            ),
            thumb_url=metric.get("img_url"),
            thumb_width=500,
            thumb_height=500
        )
        for metric in metrics
    ]
    logger.info(
        "{0} request metrics {1}".format(
            user_id, 
            ", ".join([
                create_text(
                    user_id=user_id, 
                    first_name=first_name,
                    last_name=last_name,
                    query=query,
                    params=metric
                ) for metric in metrics
            ])
        )
    )
    update.inline_query.answer(results, is_personal=True)


show_metric_handl = InlineQueryHandler(
    metric_show,
    pass_update_queue=True
)