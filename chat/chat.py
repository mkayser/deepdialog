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
    c.execute('''CREATE TABLE Chatrooms (number integer, participants integer, scenario integer)''')

    c.execute('''CREATE TABLE ActiveUsers (name text unique, room integer)''')
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
        list_scenarios = json.load(fin)
        scenarios = defaultdict(dict)
        for scenario in list_scenarios:
            scenarios[scenario["uuid"]] = scenario
    app.config["user_params"] = params
    app.config["scenarios"] = scenarios
    socketio.run(app)


