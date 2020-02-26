#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram import ParseMode


class GroupMessageForwarder():
    def __init__(self, cfg):
        self.cfg = cfg
        self.membergroupID = self.cfg["member"]
        self.admingroupID = self.cfg["admin"]
        # Save member->admin forward msg ID with original member msg ID
        self.fwdMessagePair = {}
        self.fwdMessagePair_rev = {}
        # Save admin->member reply msg ID with original admin msg ID
        self.repMessagePair = {}
        self.repMessagePair_rev = {}
        self.help_text =  """管理群Bot使用说明：
`/help` 显示本帮助
`/getid` 拉取会话ID，调试用。"""
        if self.cfg["admin_manager"]:
            self.help_text += """
--------------------------------
`/admin add` 在成员群中将自己设置管理员。
`/admin del` 在成员群中将自己移除管理员。
`/admin invite` 获得一个永久有效的邀请链接"""
        if self.cfg["message_forwarding"]:
            self.help_text += """
--------------------------------
本bot将自动把成员群的消息转发到本群（管理群）中
对转发消息的回复将同步到成员群中"""
        if self.cfg["greetings_auto"]:
            self.help_text += """
--------------------------------
当成员群有新人时，本bot将自动发送欢迎消息"""

    def helpAdmin(self, update, context):
        """Send a message when the command /help is issued."""
        update.message.reply_markdown(self.help_text)

    def adminManage(self, update, context):
        if not self.cfg["admin_manager"]:
            self.helpAdmin(update, context)
            return
        # See command type
        msg = update.message
        cmds = msg.text.split(maxsplit=3)
        if len(cmds) < 2:
            self.helpAdmin(update, context)
            return

        user = msg.from_user
        if cmds[1] == "add":
            r = context.bot.promote_chat_member(
                chat_id = self.cfg["member"], 
                user_id = user.id,
                can_change_info=True, can_invite_users=True, can_restrict_members=True, can_pin_messages=True, can_promote_members=True
            )
        elif cmds[1] == "del":
            r = context.bot.promote_chat_member(
                chat_id = self.cfg["member"], 
                user_id = user.id,
                can_change_info=False, can_invite_users=False, can_restrict_members=False, can_pin_messages=False, can_promote_members=False
            )
        elif cmds[1] == "invite":
            r = context.bot.export_chat_invite_link(self.cfg["member"])
            if r:
                r = msg.reply_markdown("您获得了法宝：[加群链接](%s)"%r)
                r = None
        elif cmds[1] == "debug": # small debug backdoor to see internal structs
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
            adminfwdmsg_id = self.fwdMessagePair_rev.get(msg.message_id)
            if not adminfwdmsg_id:
                return
            # prep 2. Alert that forwarded message
            context.bot.send_message(self.admingroupID, "**这条消息被修改了**。新消息：",
                                     parse_mode=ParseMode.MARKDOWN, reply_to_message_id=adminfwdmsg_id)
            # prep 3. Remove from DB
            self.fwdMessagePair_rev.pop(msg.message_id)
            self.fwdMessagePair.pop(adminfwdmsg_id)
        elif update.message:  # if sending new message
            # If member sending new message
            msg = update.message
            # prep 1. See if member replying to previous bot message
            if msg.reply_to_message:
                nmsg = msg.reply_to_message
                nmsg_id = self.repMessagePair.get(nmsg.message_id)
                if not nmsg_id:  # or it might be member's message?
                    nmsg_id = self.fwdMessagePair_rev.get(nmsg.message_id)
                # prep 1.1: have an alert
                if nmsg_id:
                    context.bot.send_message(self.admingroupID, "**这条消息被回复了**。回复消息：",
                                             parse_mode=ParseMode.MARKDOWN, reply_to_message_id=nmsg_id)
        # 1. confirm it
        if not msg.chat_id == self.membergroupID:
            return
        # 2. forward to admin channel
        newmsg = msg.forward(self.admingroupID)
        # update it
        self.fwdMessagePair[newmsg.message_id] = msg.message_id
        self.fwdMessagePair_rev[msg.message_id] = newmsg.message_id

    def roleAdmin(self, update, context):
        if not self.cfg["message_forwarding"]:
            return
        if update.edited_message:
            # If admin edit a message, delete old one and send again
            msg = update.edited_message
            # prep 1. find the forwarded message in Member group, if any
            memberfwdmsg_id = self.repMessagePair_rev.get(msg.message_id)
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
        msg_rid = self.fwdMessagePair.get(msg.reply_to_message.message_id)
        # Only reply to messages we had sent and recorded
        if not msg_rid:
            return
        # 3. reply
        newmsg = context.bot.send_message(
            self.membergroupID, msg.text, reply_to_message_id=msg_rid)
        # 4. update
        self.repMessagePair[newmsg.message_id] = msg.message_id
        self.repMessagePair_rev[msg.message_id] = newmsg.message_id
