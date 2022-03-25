from telegram.ext import (
    Updater, 
)
from telegram import (
    Bot,
    Update,
)

import json
import logging
import os

from ydb_persistence import YDBPersistence

from handlers.metric_add import add_metric_handl
from handlers.metric_show import show_metric_handl
from handlers.misc import start_handl, update_config_first


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    persistent_bot_state = YDBPersistence()
    bot = Bot(token=os.environ.get("BOT_TOKEN"))
    updater = Updater(
        bot=bot, 
        use_context=True,
        persistence=persistent_bot_state
    )
    dispatcher = updater.dispatcher  

    dispatcher.add_handler(start_handl)
    dispatcher.add_handler(show_metric_handl)
    dispatcher.add_handler(add_metric_handl)

    updater.job_queue.run_once(update_config_first, when=0)

    upd = Update.de_json(json.loads(event["body"]), dispatcher.bot)

    dispatcher.update_persistence(
        upd
    )
    dispatcher.process_update(
       upd 
    )
    
    return {
        'statusCode': 200,
        'body': 'Hello World!',
    }

