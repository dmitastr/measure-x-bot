import os
import json
from telegram import Update, TelegramObject
from main import setup

dispatcher = setup(token=os.environ.get("BOT_TOKEN"))

def handler(event, context):
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

