#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup


class GroupMessageForwarder():
    def __init__(self, cfg, db):
        self.cfg = cfg
        self.db = db
        self.membergroupID = self.cfg["member"]
        self.admingroupID = self.cfg["admin"]
        self.help_text = """啵叽的帮助：
`/help` 显示本帮助
`/getid` 拉取会话ID，调试用。"""
        if self.cfg["message_forwarding"]:
            self.help_text += """
--------------------------------
本bot将自动把成员群的消息转发到本群（管理群）中
对转发消息的回复将同步到成员群中"""
        if self.cfg["greetings_auto"]:
            self.help_text += """
--------------------------------
当成员群有新人时，本bot将自动发送欢迎消息"""

        # Register all handlers
        self._command_handlers = {}
        if self.cfg["admin_cmds"]:
            self._command_handlers["add"] = self.admin_add
            self._command_handlers["del"] = self.admin_del
            self._command_handlers["invite"] = self.admin_invite
            self.help_text += """
--------------------------------
成员群管理功能已经启动。在管理员群中发送消息：
`/admin add` 在成员群中将自己设置管理员。
`/admin del` 在成员群中将自己移除管理员。
`/admin invite` 获得一个永久有效的Members群邀请链接"""
        if self.cfg["silent_mode"]:
            # Start invite link scheduler
            self._admin_invite_link_scheduler_up = False
            self._admin_invite_link = ""
            self._command_handlers["register"] = self.admin_register
            self._command_handlers["deregister"] = self.admin_register
            self.help_text += """
--------------------------------
本bot目前工作在静默模式下。
在静默模式中，您可以在管理群发送：
`/admin register` 加入静默模式
`/admin deregister` 退出静默模式
若您已经加入了静默模式，可对bot私聊发送：
`%s` 获取加入Admin群的邀请链接""" % (self.cfg["silent_key"])

    def _reload_admin_invite(self, context):
        self._admin_invite_link = context.bot.export_chat_invite_link(
            self.cfg["admin"])

    def helpAdmin(self, update, context):
        """Send a message when the command /help is issued."""
        update.message.reply_markdown(self.help_text)

    def admin_add(self, update, context, cmds):
        return context.bot.promote_chat_member(
            chat_id=self.cfg["member"],
            user_id=update.message.from_user.id,
            can_change_info=True, can_invite_users=True, can_restrict_members=True, can_pin_messages=True, can_promote_members=True
        )

    def admin_del(self, update, context, cmds):
        return context.bot.promote_chat_member(
            chat_id=self.cfg["member"],
            user_id=update.message.from_user.id,
            can_change_info=False, can_invite_users=False, can_restrict_members=False, can_pin_messages=False, can_promote_members=False
        )

    def admin_invite(self, update, context, cmds):
        r = context.bot.export_chat_invite_link(self.cfg["member"])
        if r:
            r = update.message.reply_markdown("您获得了法宝：[加群链接](%s)" % r)
            r = None
        return r

    def admin_register(self, update, context, cmds):
        if not self.cfg["silent_mode"]:
            return
        if cmds[1] == "register":
            self.db.admin_config(update.message.from_user.id, 1)
        elif cmds[1] == "deregister":
            self.db.admin_config(update.message.from_user.id, 0)
        else:
            raise ValueError("Handler sent wrong message to me")
        return True

    def silentMessage(self, update, context):
        if not self.cfg["silent_mode"]:
            return
        t = update.message.text
        if t.strip() != self.cfg["silent_key"]:
            return
        # Test if admin
        if not self.db.admin_test(update.message.from_user.id):
            return
        # Start the scheduler if not up yet
        if not self._admin_invite_link_scheduler_up:
            self._reload_admin_invite(context)
            context.job_queue.run_repeating(self._reload_admin_invite, 180)
            self._admin_invite_link_scheduler_up = True
        update.message.reply_text("点击按钮进入管理群。链接过期失效，若无法使用请重新申请。",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                                      text="加入群聊",
                                      url=self._admin_invite_link
                                  )]]))

    def adminManage(self, update, context):
        if not self.cfg["admin_cmds"]:
            self.helpAdmin(update, context)
            return
        # See command type
        msg = update.message
        cmds = msg.text.split(maxsplit=3)
        if len(cmds) < 2:
            self.helpAdmin(update, context)
            return
        handler = self._command_handlers.get(cmds[1])

        r = None
        if not handler == None:
            r = handler(update, context, cmds)
        elif cmds[1] == "debug":  # small debug backdoor to see internal structs
            pass
            m = context.bot.get_chat(self.cfg["member"])
            m = m.get_administrators()
            msg.reply_markdown("*苟利国家生死以 岂因祸福避趋之*")
        else:
            self.helpAdmin(update, context)
            return
        if r == None:
            pass
        elif r == True:
            msg.reply_markdown("设置成功")
        elif r == False:
            msg.reply_markdown("设置失败")

    def greetings(self, update, context):
        if not self.cfg["greetings_auto"]:
            return
        msg = update.message
        if msg.new_chat_members:
            msg.reply_markdown(self.cfg["greetings"])
            return

    def roleMember(self, update, context):
        if not self.cfg["message_forwarding"]:
            return
        if update.edited_message:
            # If member edit a message, send an alert
            msg = update.edited_message
            # prep 1. Find the forwarded message in Admin group
            adminfwdmsg_id = self.db.get_message_record(
                "admin", rightID=msg.message_id)
            if not adminfwdmsg_id:
                return
            # prep 2. Alert that forwarded message
            context.bot.send_message(self.admingroupID, "**这条消息被修改了**。新消息：",
                                     parse_mode=ParseMode.MARKDOWN, reply_to_message_id=adminfwdmsg_id)
            # prep 3. Remove from DB? considering it
            self.db.remove_message_record(
                "admin", adminfwdmsg_id, msg.message_id)
        elif update.message:  # if sending new message
            # If member sending new message
            msg = update.message
            # prep 1. See if member replying to previous bot message
            # If so, add a hint
            if msg.reply_to_message:
                nmsg = msg.reply_to_message
                nmsg_id = self.db.get_message_record(
                    "member", leftID=nmsg.message_id)
                if not nmsg_id:  # or it might be member's message?
                    nmsg_id = self.db.get_message_record(
                        "admin", rightID=nmsg.message_id)
                # prep 1.1: have an alert
                if nmsg_id:
                    context.bot.send_message(self.admingroupID, "**这条消息被回复了**。回复消息：",
                                             parse_mode=ParseMode.MARKDOWN, reply_to_message_id=nmsg_id)
        # 1. confirm it
        if not msg.chat_id == self.membergroupID:
            return
        # 2. forward to admin channel
        newmsg = msg.forward(self.admingroupID)
        # We send a new message in Admin group.
        # New message id of admin group is LEFT
        # The message id related in member group is RIGHT
        self.db.insert_message_record(
            "admin", newmsg.message_id, msg.message_id)

    def roleAdmin(self, update, context):
        if not self.cfg["message_forwarding"]:
            return
        if update.edited_message:
            # If admin edit a message, delete old one and send again
            msg = update.edited_message
            # prep 1. find the forwarded message in Member group, if any
            memberfwdmsg_id = self.db.get_message_record(
                "member", rightID=msg.message_id)
            if not memberfwdmsg_id:
                return
            # prep 2. Edit the message
            context.bot.edit_message_text(
                msg.text, chat_id=self.membergroupID, message_id=memberfwdmsg_id)
            # edit do not change much so leave now
            return
        elif update.message:
            # If admin send a message, maybe some message is replied.
            msg = update.message
            # prep 1. check if this is a reply message
            if not msg.reply_to_message:
                return
        # 1. confirm it
        if not msg.chat_id == self.admingroupID:
            return
        # 2. get original message ID
        msg_rid = self.db.get_message_record(
            "admin", leftID=msg.reply_to_message.message_id)
        # Only reply to messages we had sent and recorded
        if not msg_rid:
            return
        # 3. reply
        newmsg = context.bot.send_message(
            self.membergroupID, msg.text, reply_to_message_id=msg_rid)
        # 4. update
        # We send a new message in Member group.
        # New message id of member group is LEFT
        # The message id related in admin group is RIGHT
        self.db.insert_message_record(
            "member", newmsg.message_id, msg.message_id)
