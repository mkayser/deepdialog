#!/bin/env python
from Queue import Queue
from collections import defaultdict
from app import create_app, socketio
import sqlite3
import os
import shutil
import json
from argparse import ArgumentParser


# initialize database with table for chat rooms and active users
def init_database(db_file):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    # number: room number, participants: number of participants (0 - 2)
    c.execute('''CREATE TABLE ActiveUsers (name text unique, status integer, status_timestamp integer, connected_status integer, connected_timestamp integer, message text, room_id integer, partner_id text, scenario_id text, agent_index integer, selected_index integer, single_task_id text, num_single_tasks_completed integer, cumulative_points integer)''')
    #c.execute('''CREATE TABLE Chatrooms (room_id integer, scenario_id text)''')
    conn.commit()
    conn.close()


def clear_data(logging_dir):
    if os.path.exists(logging_dir):
        shutil.rmtree(logging_dir)
    os.makedirs(logging_dir)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', help="File containing app configuration params", type=str,
                        default="params.json")
    parser.add_argument('--host', help="Host IP address to run app on - defaults to localhost", type=str, default="127.0.0.1")
    args = parser.parse_args()
    params_file = args.p
    with open(params_file) as fin:
        params = json.load(fin)

    if os.path.exists(params["db"]["location"]):
        os.remove(params["db"]["location"])
    init_database(params["db"]["location"])
    clear_data(params["logging"]["chat_dir"])
    app = create_app(debug=True)
    with open(params["scenarios_json_file"]) as fin:
        scenarios = json.load(fin)
        scenarios_dict = {v["uuid"]:v for v in scenarios}
    app.config["user_params"] = params
    app.config["scenarios"] = scenarios_dict
    app.config["outcomes"] = defaultdict(lambda : -1)
    app.config["waiting_users"] = Queue()
    socketio.run(app, host=args.host)


