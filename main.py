#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import toml

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

cfg = toml.load(open("config.toml", "r"))


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')

def getid(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text("Chat ID is {}".format(update.message.chat_id))

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')

messageReplyPair = {}

def greetings(update, context):
    msg = update.message
    if msg.chat_id == cfg["group"]["member"]:
        if msg.new_chat_members:
            msg.reply_markdown("""Welcome! See [this link](https://memoryhonest.github.io) about our website!""")
            return

def forwarder(update, context):
    msg = update.message
    if msg.chat_id == cfg["group"]["member"]:
        newmsg = msg.forward(cfg["group"]["admin"])
        messageReplyPair[newmsg.message_id] = msg.message_id
        return
    if msg.chat_id == cfg["group"]["admin"]:
        # maybe returned of some new message
        if msg.reply_to_message:
            msg_rid = messageReplyPair.get(msg.reply_to_message.message_id)
            # Only reply to messages we had sent and recorded
            if msg_rid:
                context.bot.send_message(cfg["group"]["member"], msg.text, reply_to_message_id = msg_rid)
            return



def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""

    # Read config
    

    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(cfg["bot"]["key"], use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("getid", getid))
    dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - forward to admin group and reply
    dp.add_handler(MessageHandler(Filters.text, forwarder))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, greetings))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
