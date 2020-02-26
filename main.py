#!/usr/bin/env python
# -*- coding: utf-8 -*-

import forwarder
import db

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


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""

    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(cfg["bot"]["key"], use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("getid", getid))
    # dp.add_handler(CommandHandler("help", help))

    # Add admin group handler
    for k in cfg["groups"]:
        v = cfg["groups"][k]
        if not v["enabled"]:
            continue
        # FIXME the database location is fixed
        # Init database
        d = db.DB(cfg["db"])
        h = forwarder.GroupMessageForwarder(v, d)
        # Greeting message
        dp.add_handler(group=0, handler=MessageHandler(
            filters=(Filters.status_update.new_chat_members &
                     Filters.chat(v["member"])),
            callback=h.greetings))
        # Forwarding ability
        dp.add_handler(group=1, handler=MessageHandler(
            filters=(Filters.text & Filters.chat(v["member"])),
            callback=h.roleMember))
        dp.add_handler(group=1, handler=MessageHandler(
            filters=(Filters.text & Filters.chat(v["admin"])),
            callback=h.roleAdmin))
        # Help command
        dp.add_handler(group=2, handler=CommandHandler(
            "help",
            filters=(Filters.command & Filters.chat(v["admin"])),
            callback=h.helpAdmin))
        # Admin commands
        dp.add_handler(group=2, handler=CommandHandler(
            "admin",
            filters=(Filters.command & Filters.chat(v["admin"])),
            callback=h.adminManage))
        # # Silent mode
        # dp.add_handler(group=0, handler=MessageHandler(
        #     filters=(Filters.private)),
        #     callback=h.silentMessage)
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
