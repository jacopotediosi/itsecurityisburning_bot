import logging
import MySQLdb
import os
import time
from apscheduler.triggers.cron import CronTrigger
from datetime import timedelta
from MySQLdb.constants import CR as MySQLdb_CR
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CallbackContext, CallbackQueryHandler, CommandHandler, ContextTypes
from typing import cast, List, Tuple, Union


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


while True:
    try:
        db = MySQLdb.connect(
            host     = os.environ.get("MYSQL_HOST"),
            user     = os.environ.get("MYSQL_USER"),
            password = os.environ.get("MYSQL_PASSWORD"),
            database = os.environ.get("MYSQL_DATABASE"),
            autocommit=True,
            charset='utf8mb4'
        )
        break
    except MySQLdb._exceptions.OperationalError as e:
        if e.args[0] != MySQLdb_CR.CONN_HOST_ERROR:
            raise
        logging.info("Waiting for DB to go UP...")
        time.sleep(10)
cursor = db.cursor()


def build_menu(
    buttons: List[InlineKeyboardButton]=[],
    n_cols: int=1,
    header_buttons: Union[InlineKeyboardButton, List[InlineKeyboardButton]]=None,
    footer_buttons: Union[InlineKeyboardButton, List[InlineKeyboardButton]]=None
) -> List[List[InlineKeyboardButton]]:
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons if isinstance(header_buttons, list) else [header_buttons])
    if footer_buttons:
        menu.append(footer_buttons if isinstance(footer_buttons, list) else [footer_buttons])
    return menu


START_MESSAGE_TEXT = """
*Welcome to @itsecurityisburning\_bot\!*

*What this bot does*
At selected times it sends via pm a random sentence extracted from [the famous video "Frangetta vs storialoffa IT Security Is Burning"](https://www.youtube.com/watch?v=k6UPUwOm6es)\.

*How to use it*
Just choose the times you want to receive messages using the menu below and let the meme go on\.

*Credits*
Made by @jacopomii\.

Dedicated to little Laura, Fabrizio Moro fan, who is keeping me so much company in this period\. From a distance I have no other way to show you how much I like you, other than by spending time with these things\.

[Source code](https://github.com/jacopotediosi/itsecurityisburning_bot)"""


def generate_start_menu(chat_id: int, keyboard_opened: bool=False):
    if keyboard_opened:
        cursor.execute("SELECT hour FROM notification_times WHERE chat_id='%s'", (chat_id,))
        hours = cursor.fetchall()
        button_list = [
            InlineKeyboardButton(
                f"{i:02d} {'✅' if ((i,) in hours) else '❌'}",
                callback_data=(i, ((i,) in hours))
            ) for i in range(24)
        ]
        return InlineKeyboardMarkup(build_menu(buttons=button_list, n_cols=6, footer_buttons=InlineKeyboardButton("DONE", callback_data="CLOSE")))
    else:
        return InlineKeyboardMarkup(build_menu(footer_buttons=InlineKeyboardButton("SET MESSAGE TIMES", callback_data="OPEN")))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=START_MESSAGE_TEXT, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True, reply_markup=generate_start_menu(update.effective_chat.id))


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data=="CLOSE":
        await query.edit_message_text(text=START_MESSAGE_TEXT, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True, reply_markup=generate_start_menu(update.effective_chat.id, False))
    elif query.data=="OPEN":
        await query.edit_message_text(text=START_MESSAGE_TEXT, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True, reply_markup=generate_start_menu(update.effective_chat.id, True))
    else:
        answer = cast(Tuple[int, bool], query.data)
        if answer[1]:
            cursor.execute("DELETE FROM notification_times WHERE chat_id='%s' AND hour='%s'", (update.effective_chat.id, answer[0]))
        else:
            cursor.execute("INSERT INTO notification_times SET chat_id='%s', hour='%s'", (update.effective_chat.id, answer[0]))
        await query.edit_message_text(text=START_MESSAGE_TEXT, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True, reply_markup=generate_start_menu(update.effective_chat.id, True))


async def send_scheduled_messages(context: CallbackContext):
    cursor.execute("SELECT message FROM notification_messages ORDER BY RAND() LIMIT 1")
    random_message = cursor.fetchone()[0]

    cursor.execute("SELECT chat_id FROM notification_times WHERE hour=HOUR(NOW())")
    for chat_id in cursor.fetchall():
        await context.bot.send_message(chat_id=chat_id[0], text=random_message)


if __name__ == '__main__':
    application = ApplicationBuilder().token(os.environ.get("BOT_TOKEN","")).arbitrary_callback_data(True).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    application.add_handler(CallbackQueryHandler(start_callback))

    job_queue = application.job_queue
    job_queue.run_custom(callback=send_scheduled_messages,job_kwargs={"trigger" : CronTrigger.from_crontab ( '1 * * * *' )}) 

    application.run_polling()