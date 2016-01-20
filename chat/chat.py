#!/bin/env python
from collections import defaultdict
from app import create_app, socketio
import sqlite3
import os
import shutil
import json
from argparse import ArgumentParser


# initialize database with table for chat rooms and active users
def init_database(params):
    conn = sqlite3.connect(params["CHAT_ROOM_DB"])
    c = conn.cursor()
    # number: room number, participants: number of participants (0 - 2)
    c.execute('''CREATE TABLE Chatrooms (number integer, participants integer, scenario text)''')
    c.execute('''CREATE TABLE ActiveUsers (name text unique, room integer, agentid integer, partner text)''')
    conn.commit()
    conn.close()


def clear_data(params):
    if os.path.exists(params["CHAT_DIRECTORY"]):
        shutil.rmtree(params["CHAT_DIRECTORY"])
    os.makedirs(params["CHAT_DIRECTORY"])

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', help="File containing app configuration params", type=str,
                        default="params.json")
    args = parser.parse_args()
    params_file = args.p
    with open(params_file) as fin:
        params = json.load(fin)

    if os.path.exists(params["CHAT_ROOM_DB"]):
        os.remove(params["CHAT_ROOM_DB"])
    init_database(params)
    clear_data(params)
    app = create_app(debug=True)
    with open(params["scenarios_json_file"]) as fin:
        scenarios = json.load(fin)
        scenarios_dict = {v["uuid"]:v for v in scenarios}
    app.config["user_params"] = params
    app.config["scenarios"] = scenarios_dict
    app.config["outcomes"] = defaultdict(lambda : -1)
    socketio.run(app)


