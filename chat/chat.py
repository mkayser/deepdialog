#!/bin/env python
from app import create_app, socketio, constants
import sqlite3
import os
import shutil
app = create_app(debug=True)


def init_databases():
    conn = sqlite3.connect(constants.CHAT_ROOM_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE Chatrooms (number integer, player1 text, player2 text, participants integer)''')
    c.execute('''CREATE TABLE ActiveUsers (name text, room integer)''')
    conn.commit()
    conn.close()

def clear_data():
    if os.path.exists(constants.CHAT_DIRECTORY):
        shutil.rmtree(constants.CHAT_DIRECTORY)
    os.makedirs(constants.CHAT_DIRECTORY)

if __name__ == '__main__':
    if os.path.exists(constants.CHAT_ROOM_DB):
        os.remove(constants.CHAT_ROOM_DB)
    init_databases()
    clear_data()
    socketio.run(app)


