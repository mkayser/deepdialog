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
            try:
                u=self._get_user_info(cursor, userid, assumed_status=None)
            except StatusChangedException:
                u = self._get_user_info_unchecked(self, cursor, userid)
                if u.status == Status.Waiting:
                    self._transition_to_single_task(cursor, userid)
                elif u.status == Status.SingleTask:
                    # Do nothing in case of timeout for SingleTask
                    pass
                elif u.status == Status.Chat:
                    self._end_chat_and_transition_to_waiting(cursor, userid)
                elif u.status == Status.Finished:
                    # Do nothing in case of timeout for SingleTask
                    pass
                else:
                    raise Exception("Unknown status: {} for user: {}".format(u.status, userid))
                

            # TODO do the status update
            cursor.execute('''SELECT status FROM ActiveUsers WHERE name=?''', (userid,))
            entry = cursor.fetchone()
            return entry[0]
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")


    def _transition_to_single_task(cursor, userid):
        #TODO
        pass
            
    def end_chat_and_transition_to_waiting(cursor, userid):
        #TODO
        pass

    def get_chat_info(self, userid):
        with self.conn:
            cursor = self.conn.cursor()
            u = _get_user_info(cursor, userid, assumed_status=Status.Chat)

            num_seconds_remaining = (self.config["status_params"]["chat"]["num_seconds"] + u.status_timestamp) - current_timestamp_in_seconds()
            scenario = self.scenarios[u.scenario_id]
            return UserChatSession(room_id, u.agent_index, scenario, num_seconds_remaining)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_single_task_info(self, userid):
        with self.conn:
            cursor = self.conn.cursor()
            u = _get_user_info(cursor, userid, assumed_status=Status.SingleTask)

            num_seconds_remaining = (self.config["status_params"]["single_task"]["num_seconds"] + u.status_timestamp) - current_timestamp_in_seconds()
            scenario = self.scenarios[u.single_task_id]

            return SingleTaskSession(scenario, u.agent_index, num_seconds_remaining)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_waiting_info(self, userid):
        with self.conn:
            cursor = self.conn.cursor()
            u = _get_user_info(cursor, userid, assumed_status=Status.Waiting)
            num_seconds = (self.config["status_params"]["waiting"]["num_seconds"] + u.status_timestamp) - current_timestamp_in_seconds()
            return WaitingSession(message, num_seconds)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_finished_info(self, userid):
        with self.conn:
            cursor = self.conn.cursor()
            u = _get_user_info(cursor, userid, assumed_status=Status.Finished)
            num_seconds = (self.config["status_params"]["finished"]["num_seconds"] + u.status_timestamp) - current_timestamp_in_seconds()
            return FinishedSession(u.message, num_seconds)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def is_chat_valid(self, userid):
        # TODO: update the connected_status and connected_timestamp
        pass

    def connect(self, userid):
        # TODO: update the connected_status and connected_timestamp
        pass
    
    def disconnect(self, userid):
        # TODO: update the connected_status and connected_timestamp
        pass

    def pick_restaurant(self, userid, restaurant_index):
        def _get_points(scenario, agent_index, restaurant_name):
            return next(obj["utility"] for obj in scenario["agents"][agent_index]["sorted_restaurants"] if obj["name"]==restaurant_name)

        def _user_finished(cursor, userid, prev_points, my_points, other_points):
            status = Status.Finished
            message = "Great, you've finished the chat! You scored {} points and your partner scored {} points.".format(my_points, other_points)
            self._update_user(cursor, userid, status=Status.Finished, message=message, cumulative_points=prev_points+my_points)
            
        try:
            with self.conn:
                cursor = self.conn.cursor()
                u = _get_user_info(cursor, userid, assumed_status=Status.Chat)

                cursor.execute("SELECT name, selected_index,cumulative_points FROM ActiveUsers WHERE room=? AND name!=?", (u.room_id, userid))
                other_userid, other_restaurant_index, other_P = cursor.fetchone()[0]

                P = u.cumulative_points
                scenario = self.scenarios[u.single_task_id]
                restaurant_name = scenario["restaurants"][restaurant_index]["name"]
                
                if u.restaurant_index == other_restaurant_index:
                    # Match
                    Pdelta       = _get_points(scenario, u.agent_index, restaurant_name)
                    other_Pdelta = _get_points(scenario, 1-u.agent_index, restaurant_name)
                    _user_finished(cursor, userid, P, Pdelta, other_Pdelta) 
                    _user_finished(cursor, other_userid, other_P, other_Pdelta, Pdelta) 
                    return restaurant_name, True
                else:
                    # Non match
                    return restaurant_name, False

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def _validate_status_or_throw(self, assumed_status, status):
        if status != assumed_status:
            raise StatusChangedException()
        return 

    def _validate_no_timeout_or_throw(self, status, status_timestamp):
        N = self.config["status_params"][Status._names[status]]["num_seconds"]
        num_seconds_remaining = (N + status_timestamp) - current_timestamp_in_seconds()
        if num_seconds_remaining>=0:
            return 
        else:
            raise StatusChangedException()

    def _update_user(self, cursor, userid, **kwargs):
        if "status" in kwargs:
            kwargs["status_timestamp"] = current_timestamp_in_seconds()
        keys = sorted(kwargs.keys())
        values = [kwargs[k] for k in keys]

        set_string = ", ".join(["{}=?".format(k) for k in keys])

        cursor.execute("UPDATE ActiveUsers SET {} WHERE name=?".format(set_string), tuple(values + [userid]))

    def _get_user_info_unchecked(self, cursor, userid):
        cursor.execute("SELECT * FROM ActiveUsers WHERE name=?", (userid,))
        u = User(cursor.fetchone())
        return u

    def _get_user_info(self, cursor, userid, assumed_status=None):
        u = self._get_user_info_unchecked(cursor, userid)
        if assumed_status is not None:
            self._validate_status_or_throw(assumed_status, u.status)
        self._validate_no_timeout_or_throw(u.status, u.status_timestamp)
        return u

    def submit_single_task(self, userid, user_input):
        def _complete_task_and_wait(cursor, userid, num_finished):
            message = "Great, you've finished {} exercises! Waiting a few seconds for a partner to chat with...".format(num_finished)
            self._update_user(cursor, userid, status=Status.Waiting, message=message, num_single_tasks_completed=num_finished)

        def _complete_task_and_finished(cursor, userid, num_finished):
            message = "Great, you've finished {} exercises!".format(num_finished)
            self._update_user(cursor, userid, status=Status.Finished, message=message, num_single_tasks_completed=num_finished)

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
        # TODO
        pass

    def attempt_join_room(self, userid):
        def _get_other_waiting_users(cursor, userid):
            # NOTE: we could try to handle single task as another waiting mode
            #       we could also even interrupt single task mode (requires e.g. periodic polling by client during SingleTask mode)
            cursor.execute("SELECT name FROM ActiveUsers WHERE name!=? AND status=?", (userid,Status.Waiting))
            userids = [r[0] for r in cursor.fetchall()]
            return userids

        def _get_max_room_id(cursor):
            cursor.execute("SELECT MAX(room_id) FROM ActiveUsers", ())
            return cursor.fetchone()[0]

        try:
            with self.conn:
                cursor = self.conn.cursor()
                u = _get_user_info(cursor, userid, assumed_status=Status.Waiting)
                others = _get_other_waiting_users(cursor, userid)
                if len(others)>0:
                    other_userid = random.choice(others)
                    next_room_id = _get_max_room_id(cursor)+1
                    self._update_user(cursor, userid, status=Status.Chat, room_id=next_room_id, message="")
                    self._update_user(cursor, other_userid, Status.Chat, room_id=next_room_id, message="")
                    return next_room_id
                else:
                    return None
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")
