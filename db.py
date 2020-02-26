#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3

class DB():
    def __init__(self, name):
        self.db = sqlite3.connect(name)
        if not self.db:
            raise ValueError("Can not open DB")
        c = self.db.cursor()
        # Create message table
        c.execute(''' CREATE TABLE IF NOT EXISTS message_record(
                            ID INT PRIMARY KEY NOT NULL,
                            SENDER_SIDE TEXT NOT NULL,
                            LEFT_ID TEXT NOT NULL,
                            RIGHT_ID INT NOT NULL) ''')
        # Create admin table
        c.execute(''' CREATE TABLE IF NOT EXISTS admins(
                            ID INT PRIMARY KEY NOT NULL,
                            USERID TEXT NOT NULL,
                            LEFT_ID TEXT NOT NULL,
                            RIGHT_ID INT NOT NULL) ''')
        self.db.commit()
        c.close()
    
    def insert_message_record(self, sender, leftID, rightID):
        c = self.db.cursor()
        c.execute('INSERT INTO message_record VALUES (NULL,?,?,?)', sender, leftID, rightID)
        self.db.commit()

    def __del__(self):
        self.db.Close()