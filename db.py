#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mysql.connector


class DB():
    def __init__(self, cfg):
        self.db = mysql.connector.connect(
            username=cfg["username"], password=cfg["password"], database=cfg["database"], host=cfg["host"], port=cfg["port"])
        if not self.db:
            raise ValueError("Can not open DB")
        c = self.db.cursor()
        try:
            # Create message table
            c.execute(''' CREATE TABLE IF NOT EXISTS message_record(
                                ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                                SENDER_LOCATION TEXT NOT NULL,
                                LEFT_ID TEXT NOT NULL,
                                RIGHT_ID INT NOT NULL,
                                IS_DELETE INT NOT NULL) ''')
            # Create admin table
            c.execute(''' CREATE TABLE IF NOT EXISTS admins(
                                ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                                USERID INT NOT NULL UNIQUE,
                                IS_DELETE INT NOT NULL) ''')
        finally:
            self.db.commit()
            c.close()

    """
    action: 1=add admin, 0=del admin
    """

    def admin_config(self, adminID, action):
        action = 0 if action == 1 else 1
        c = self.db.cursor()
        try:
            c.execute('INSERT INTO admins (userid, is_delete) '
                      'VALUES (%s, %s) '
                      'ON DUPLICATE KEY UPDATE is_delete = %s', (adminID, action, action))
        finally:
            self.db.commit()
            c.close()

    def insert_message_record(self, location, leftID, rightID):
        c = self.db.cursor()
        try:
            c.execute('INSERT INTO message_record '
                      '(sender_location, left_id, right_id, is_delete) '
                      'VALUES (%s,%s,%s,0)', (location, leftID, rightID))
        finally:
            self.db.commit()
            c.close()

    def get_message_record(self, location, leftID=None, rightID=None):
        if leftID == None and rightID == None:
            raise ValueError("Invalid input parameters. Should have one value")
        if not (leftID == None or rightID == None):
            raise ValueError("Both ID provided")
        c = self.db.cursor()
        try:
            if leftID == None:
                v = c.execute('SELECT left_id FROM message_record WHERE '
                              'is_delete = 0 AND sender_location = %s AND right_id = %s',
                              (location, rightID))
            else:
                v = c.execute('SELECT right_id FROM message_record WHERE '
                              'is_delete = 0 AND sender_location = %s AND left_id = %s', (location, leftID))
            v = c.fetchone()
            if v == None:
                return None
            if len(v) != 1:
                raise ValueError("Strange value returned by SQLite")
        finally:
            self.db.commit()
            c.close()
        return v[0]

    def remove_message_record(self, location, leftID, rightID):
        c = self.db.cursor()
        c.execute('UPDATE message_record SET is_delete = 1 WHERE '
                  'is_delete = 0 AND sender_location = %s '
                  'AND left_id = %s AND right_id = %s', (location, leftID, rightID))
        self.db.commit()
        c.close()

    def __del__(self):
        self.db.Close()
