from __future__ import with_statement
import random
import sqlite3
from .utils import UserChatSession, SingleTaskSession, FinishedSession, WaitingSession
import datetime
import time
from flask import current_app as app

class Status(object):
    Waiting, Chat, SingleTask, Finished = range(4)
    _names = ["waiting","chat","single_task","finished"]

def current_timestamp_in_seconds():
    return int(time.mktime(datetime.datetime.now().timetuple()))

class StatusChangedException(Exception):
    pass

class User(object):
    def __init__(self, row):
        self.name = row[0]
        self.status = row[1]
        self.status_timestamp = row[2]
        self.connected_status = row[3]
        self.connected_timestamp = row[4]
        self.message = row[5]
        self.room_id = row[6]
        self.scenario_id = row[7]
        self.agent_index = row[8]
        self.selected_index = row[9]
        self.single_task_id = row[10]
        self.num_single_tasks_completed = row[11]
        self.cumulative_points = row[12]

    

class BackendConnection(object):
    def __init__(self, config, scenarios):
        self.config = config
        self.conn = sqlite3.connect(config["db"]["location"])
        self.scenarios = scenarios

    def close(self):
        self.conn.close()
        self.conn = None

    def create_user_if_necessary(self, username):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO ActiveUsers VALUES (?,?,?,?,?,?)''', (username, Status.Waiting, 0, -1, '',0))

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
            cursor.execute('''SELECT status,status_timestamp,room_id,scenario_id,agent_index FROM ActiveUsers WHERE name=?''', (userid,))
            status,status_timestamp,room_id,scenario_id,agent_index = cursor.fetchone()
            num_seconds_remaining = (self.config["status_params"]["chat"]["num_seconds"] + status_timestamp) - current_timestamp_in_seconds()

            self._validate_status_or_throw(Status.Chat, status, status_timestamp)

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
            self._validate_status_or_throw(Status.SingleTask, status, status_timestamp)
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
            self._validate_status_or_throw(Status.Waiting, status, status_timestamp)
            return WaitingSession(message, num_seconds)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_finished_info(self, userid):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''SELECT status,status_timestamp,message FROM ActiveUsers WHERE name=?''', (userid,))
            status,status_timestamp,message = cursor.fetchone()
            num_seconds_remaining = (self.config["status_params"]["finished"]["num_seconds"] + status_timestamp) - current_timestamp_in_seconds()
            self._validate_status_or_throw(Status.Finished, status, status_timestamp)
            return FinishedSession(message, num_seconds)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def connect(self, userid):
        # TODO: update the connected_status and connected_timestamp
        pass
    
    def disconnect(self, userid):
        # TODO: update the connected_status and connected_timestamp
        pass

    def pick_restaurant(self, userid, restaurant_index):
        def _get_points(scenario, agent_index, restaurant_name):
            return next(obj["utility"] for obj in scenario["agents"][agent_index]["sorted_restaurants"] if obj["name"]==restaurant_name)

        def _user_finished(cursor, userid, my_points, other_points):
            status = Status.Finished
            status_timestamp = current_timestamp_in_seconds()
            message = "Great, you've finished the chat! You scored {} points and your partner scored {} points.".format(my_points, other_points)
            cursor.execute("UPDATE ActiveUsers SET status=?, status_timestamp=?, cumulative_points = cumulative_points + {}, message=? WHERE name=?".format(my_points), 
                           (status, status_timestamp, message, userid))
            
        try:
            with self.conn:
                cursor = self.conn.cursor()

                cursor.execute("SELECT status, status_timestamp, room_id, scenario_id, agent_index, cumulative_points FROM ActiveUsers WHERE name=?", (userid,))
                
                status, status_timestamp, room_id, scenario_id, agent_index, cumulative_points = cursor.fetchone()
                self._validate_status_or_throw(Status.Chat, status, status_timestamp)

                cursor.execute("SELECT name, selected_index FROM ActiveUsers WHERE room=? AND name!=?", (room_id, userid))
                other_userid, other_restaurant_index = cursor.fetchone()[0]

                restaurant_name = scenario["restaurants"][restaurant_index]["name"]
                
                if restaurant_index == other_restaurant_index:
                    # Match
                    user_points       = _get_points(scenario, agent_index, restaurant_name)
                    other_user_points = _get_points(scenario, 1-agent_index, restaurant_name)
                    _user_finished(cursor, userid, user_points, other_user_points) 
                    _user_finished(cursor, other_userid, other_user_points, user_points) 
                    return restaurant_name, True
                else:
                    # Non match
                    return restaurant_name, False

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def _validate_status_or_throw(self, assumed_status, status, status_timestamp):
        if status != assumed_status:
            raise StatusChangedException()
        else:
            N = self.config["status_params"][Status._names[status]]["num_seconds"]
            num_seconds_remaining = (N + status_timestamp) - current_timestamp_in_seconds()
            if num_seconds_remaining>=0:
                return 
            else:
                raise StatusChangedException()

    def _set_status(self, cursor, userid, status, message="", additional_points=0, additional_tasks_completed=0):
        status_timestamp = current_timestamp_in_seconds()
        cursor.execute("UPDATE ActiveUsers SET status=?, status_timestamp=?, cumulative_points = cumulative_points + {}, num_single_tasks_completed = num_single_tasks_completed + {}, message=? WHERE name=?".format(additional_points, additional_tasks_completed), (status, status_timestamp, message, userid))

    def _get_user_info(self, cursor, userid, assumed_status=None):
        cursor.execute("SELECT * FROM ActiveUsers WHERE name=?", (userid,))
        u = User(cursor.fetchone())
        if assumed_status is not None:
            self._validate_status_or_throw(assumed_status, u.status, u.status_timestamp)
        return u

    def submit_single_task(self, userid, user_input):
        def _complete_task_and_wait(cursor, userid, num_finished):
            message = "Great, you've finished {} exercises! Waiting a few seconds for a partner to chat with...".format(num_finished)
            _set_status(cursor, userid, Status.Waiting, message=message, additional_tasks_completed=1)

        def _complete_task_and_finished(cursor, userid, num_finished):
            message = "Great, you've finished {} exercises!".format(num_finished)
            _set_status(cursor, userid, Status.Finished, message=message, additional_tasks_completed=1)

        try:
            with self.conn:
                cursor = self.conn.cursor()
                u = _get_user_info(cursor, userid, assumed_status=Status.SingleTask)
                if u.num_single_tasks_completed == self.config["status_params"]["single_task"]["max_tasks"]-1:
                    _complete_task_and_finished(cursor, userid, u.num_single_tasks_completed+1)
                else:
                    _complete_task_and_wait(cursor, userid, u.num_single_tasks_completed+1)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def leave_room(self, userid):
        pass

    def attempt_join_room(self, userid):
        pass

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
