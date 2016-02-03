from __future__ import with_statement
import random
import sqlite3
import app.main.utils
import datetime
import time
from flask import current_app as app

class Status(object):
    Waiting, Chat, SingleTask, Finished = range(4)

def current_timestamp_in_seconds():
    return int(time.mktime(datetime.datetime.now().timetuple()))

class StatusChangedException(Exception):
    pass

class BackendConnection(object):
    def __init__(self, config, scenarios, single_tasks):
        self.config = config
        self.conn = sqlite3.connect(config["db"]["location"])
        self.scenarios = scenarios
        self.single_tasks = single_tasks

    def close(self):
        self.conn.close()
        self.conn = None

    def create_user_if_necessary(self, username):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO ActiveUsers VALUES (?,?,?,?,?,?)''', (username, Status.Waiting, 0, 0, '',0))

    def get_status(self, userid):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''SELECT status FROM ActiveUsers WHERE name=?''', (userid,))
            entry = cursor.fetchone()
            return entry[0]
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_chat_info(self, userid):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''SELECT status,status_timestamp,room_id,agent_index FROM ActiveUsers WHERE name=?''', (userid,))
            status,status_timestamp,room_id,agent_index = cursor.fetchone()
            num_seconds_remaining = (self.config["status_params"]["chat"]["num_seconds"] + status_timestamp) - current_timestamp_in_seconds()

            if status != Status.Chat or num_seconds_remaining<=0:
                raise StatusChangedException()
            else:
                cursor.execute('''SELECT scenario_id FROM ChatRooms WHERE room_id=?''', (room_id,))
                scenario_id = cursor.fetchone()
                scenario = self.scenarios[scenario_id]
                return UserChatSession(room_id, agent_index, scenario, num_seconds_remaining)
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_single_task_info(self, userid):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''SELECT status,status_timestamp,single_task_id FROM ActiveUsers WHERE name=?''', (userid,))
            status,status_timestamp,single_task_id = cursor.fetchone()
            num_seconds_remaining = (self.config["status_params"]["single_task"]["num_seconds"] + status_timestamp) - current_timestamp_in_seconds()

            if status != Status.SingleTask or num_seconds_remaining<=0:
                raise StatusChangedException()
            else:
                single_task = self.single_tasks[single_task_id]
                return SingleTaskSession(single_task, num_seconds_remaining)
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_waiting_info(self, userid):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''SELECT status,status_timestamp,message FROM ActiveUsers WHERE name=?''', (userid,))
            status,status_timestamp,message = cursor.fetchone()
            num_seconds_remaining = (self.config["status_params"]["waiting"]["num_seconds"] + status_timestamp) - current_timestamp_in_seconds()

            if status != Status.Waiting or num_seconds_remaining<=0:
                raise StatusChangedException()
            else:
                return WaitingSession(message, num_seconds)
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_finished_info(self, userid):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''SELECT status,status_timestamp,message FROM ActiveUsers WHERE name=?''', (userid,))
            status,status_timestamp,message = cursor.fetchone()
            num_seconds_remaining = (self.config["status_params"]["finished"]["num_seconds"] + status_timestamp) - current_timestamp_in_seconds()

            if status != Status.Finished or num_seconds_remaining<=0:
                raise StatusChangedException()
            else:
                return FinishedSession(message, num_seconds)
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def pick_restaurant(self, userid, restaurant_index):
        try:
            with self.conn:
                cursor = self.conn.cursor()

                cursor.execute("SELECT status, status_timestamp, room_id, agent_index, cumulative_points FROM ActiveUsers WHERE name=?", (userid,))
                
                status, status_timestamp, room_id, agent_index, cumulative_points = cursor.fetchone()
                self._validate_status_or_throw(Status.Chat, status, status_timestamp)

                cursor.execute("SELECT selected_index FROM ActiveUsers WHERE room=? AND name!=?", (room_id, userid))
                other_selection = cursor.fetchone()[0]
                
                #TODO finish logic here
                
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def _validate_status_or_throw(self, assumed_status, status, status_timestamp):
        if status != assumed_status:
            raise StatusChangedException
        else:
            # TODO: Check for timeout
            pass
            #Waiting, Chat, SingleTask, Finished = range(4)
            #if status == Status.Waiting:
            #    pass
            

    def submit_single_task(self, userid, user_input):
        pass

    def leave_room(self, userid):
        pass

    def update_user_points(self, pairs):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                for username, points in pairs:
                    cursor.execute("UPDATE ActiveUsers SET cumulative_points = cumulative_points + {} WHERE name=?".format(points), (username,))
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def find_room_for_user_if_possible(self, username):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                # see if the current user has already been paired - a user is paired if their room != 0
                cursor.execute('''SELECT * FROM ActiveUsers WHERE name=?''', (username,))
                user_entry = cursor.fetchone()
                room_id = user_entry[1]
                if room_id != 0:
                    cursor.execute('''SELECT * FROM Chatrooms WHERE number=?''', (room_id,))
                    scenario_id = cursor.fetchone()[2]
                    agent_number = user_entry[2]
                    partner = user_entry[3]
                    return room_id, scenario_id, agent_number, partner

                # find all users who aren't currently paired (and not the current user)
                cursor.execute('''SELECT name FROM ActiveUsers WHERE room = 0 AND name!=?''', (username,))
                unpaired_users = cursor.fetchall()

                # if there are any unpaired users, pick one at random and pair
                if unpaired_users:
                    paired_user = random.choice(unpaired_users)[0]
                    app.logger.debug("Paired new user %s with %s" % (username, paired_user))
                    scenario_id = random.choice(self.scenario_ids)
                    room_id = self.assign_room(scenario_id)
                    agent_number = random.choice(range(1, 3))
                    other_agent = 1 if agent_number == 2 else 2
                    # update database to reflect that users have been assigned to these rooms
                    cursor.execute('''UPDATE ActiveUsers SET room=?,agentid=?,partner=? WHERE name=?''', (room_id, agent_number, paired_user, username))
                    cursor.execute('''UPDATE ActiveUsers SET room=?,agentid=?,partner=? WHERE name=?''', (room_id, other_agent, username, paired_user))
                    return room_id, scenario_id, agent_number, paired_user
                else:
                    return None, None, 0, None
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    # Assign a room to two paired users
    def assign_room(self, scenario_id):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                # Find any rooms with 0 participants
                cursor.execute('''SELECT number FROM Chatrooms WHERE participants = 0''')
                empty_rooms = cursor.fetchall()

                # If there are any empty (unused) rooms, assign participants to that room
                if empty_rooms:
                    r = random.choice(empty_rooms)
                    room = r[0]
                    app.logger.debug("Found empty room %d, scenario %s" % (room, scenario_id))
                    cursor.execute('''UPDATE Chatrooms SET participants=2,scenario=? WHERE number=?''', (scenario_id, room))
                else:
                    # otherwise, find the max room number and create a new room with number = max + 1
                    # (or 1 if it's the first room)
                    cursor.execute('''SELECT MAX(number) FROM Chatrooms''')
                    r = cursor.fetchone()
                    if r is None or r[0] is None:
                        room = 1
                    else:
                        room = r[0] + 1
                    cursor.execute('''INSERT INTO Chatrooms VALUES (?,2,?,-1,-1)''', (room, scenario_id))
                return room

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def leave_room(self, username, room):
        app.logger.debug("Update user %s in database" % username)
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("UPDATE Chatrooms SET participants = participants - 1,selected_restaurant_1=-1,selected_restaurant_1=-1 WHERE number=?", (room,))
                cursor.execute("UPDATE ActiveUsers SET room=-1,agentid=0,partner='' WHERE name=?", (username,))
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def select_restaurant(self, username, partner, scenario_id, outcome):
        key = utils.generate_outcome_key(username, partner, scenario_id)
        if app.config["outcomes"][key] == -1:
            app.logger.debug("Inserted new outcome %d" % outcome)
            app.config["outcomes"][key] = outcome

        partner_key = utils.generate_partner_key(username, partner, scenario_id)
        stored_outcome = app.config["outcomes"][partner_key]
        if stored_outcome != -1:
            if stored_outcome != outcome or stored_outcome == app.config["user_params"]["OUTCOME_MISMATCH"]:
                app.logger.debug("Found outcome %d already present when inserting outcome %d" % (stored_outcome, outcome))
                app.config["outcomes"][key] = app.config["user_params"]["OUTCOME_MISMATCH"]
                return -1
            else:
                return 1

        return 0

