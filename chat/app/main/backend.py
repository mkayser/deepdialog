from __future__ import with_statement
import random
import sqlite3
from .backend_utils import UserChatSession, SingleTaskSession, WaitingSession, FinishedSession
import datetime
import time
from flask import current_app as app


class Status(object):
    Waiting, Chat, SingleTask, Finished = range(4)
    _names = ["waiting", "chat", "single_task", "finished"]

    @staticmethod
    def from_str(s):
        if Status._names.index(s) == 0:
            return Status.Waiting
        if Status._names.index(s) == 1:
            return Status.Chat
        if Status._names.index(s) == 2:
            return Status.SingleTask
        if Status._names.index(s) == 3:
            return Status.Finished

    def to_str(self):
        return self._names[self]


def current_timestamp_in_seconds():
    return int(time.mktime(datetime.datetime.now().timetuple()))


class BadChatException(Exception):
    pass


class NoSuchUserException(Exception):
    pass


class UnexpectedStatusException(Exception):
    pass


class ConnectionTimeoutException(Exception):
    pass


class InvalidStatusException(Exception):
    pass


class StatusTimeoutException(Exception):
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
        self.partner_id = row[7]
        self.scenario_id = row[8]
        self.agent_index = row[9]
        self.selected_index = row[10]
        self.single_task_id = row[11]
        self.num_single_tasks_completed = row[12]
        self.cumulative_points = row[13]


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
            now = current_timestamp_in_seconds()
            cursor.execute('''INSERT OR IGNORE INTO ActiveUsers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                           (username, Status.Waiting, now, 1, now, "", -1, "", "", -1, -1, "", 0, 0))

    def is_status_unchanged(self, userid, assumed_status):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                try:
                    u = self._get_user_info(cursor, userid, assumed_status=assumed_status)
                    if u.status == Status.Waiting:
                        self.attempt_join_room(userid)
                        u = self._get_user_info(cursor, userid, assumed_status=assumed_status)
                    return True
                except (UnexpectedStatusException, ConnectionTimeoutException, StatusTimeoutException) as e:
                    return False

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_updated_status(self, userid):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                try:
                    u = self._get_user_info(cursor, userid, assumed_status=None)
                    return u.status
                except (UnexpectedStatusException, ConnectionTimeoutException, StatusTimeoutException) as e:
                    # Handle timeouts by performing the relevant update
                    u = self._get_user_info_unchecked(cursor, userid)
                    if u.status == Status.Waiting:
                        self._transition_to_single_task(cursor, userid)
                        return Status.SingleTask
                    elif u.status == Status.SingleTask:
                        return u.status
                    elif u.status == Status.Chat:
                        if isinstance(e, ConnectionTimeoutException):
                            message = "Your partner's connection has timed out! Waiting for a new chat..."
                        else:
                            message = "Darn, you ran out of time! Waiting for a new chat..."
                        self._end_chat_and_transition_to_waiting(cursor, userid, u.partner_id, message=message,
                                                                 partner_message=message)
                        return Status.Waiting
                    elif u.status == Status.Finished:
                        self._update_user(cursor, userid, status=Status.Waiting)
                        return Status.Waiting
                    else:
                        raise Exception("Unknown status: {} for user: {}".format(u.status, userid))

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def _transition_to_single_task(self, cursor, userid):
        scenario_id = random.choice(self.scenarios.keys())
        my_agent_index = random.choice([0, 1])
        self._update_user(cursor, userid,
                          status=Status.SingleTask,
                          single_task_id=scenario_id,
                          agent_index=my_agent_index,
                          selected_index=-1,
                          message="")

    def _end_chat_and_transition_to_waiting(self, cursor, userid, partner_id, message, partner_message):
        self._update_user(cursor, userid,
                          status=Status.Waiting,
                          room_id=-1,
                          message=message)
        self._update_user(cursor, partner_id,
                          status=Status.Waiting,
                          room_id=-1,
                          message=partner_message)

    def get_chat_info(self, userid):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                u = self._get_user_info(cursor, userid, assumed_status=Status.Chat)
                num_seconds_remaining = (self.config["status_params"]["chat"][
                                             "num_seconds"] + u.status_timestamp) - current_timestamp_in_seconds()
                scenario = self.scenarios[u.scenario_id]
                return UserChatSession(u.room_id, u.agent_index, scenario, num_seconds_remaining)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_single_task_info(self, userid):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                u = self._get_user_info(cursor, userid, assumed_status=Status.SingleTask)
                num_seconds_remaining = (self.config["status_params"]["single_task"][
                                             "num_seconds"] + u.status_timestamp) - current_timestamp_in_seconds()
                scenario = self.scenarios[u.single_task_id]
                return SingleTaskSession(scenario, u.agent_index, num_seconds_remaining)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_waiting_info(self, userid):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                u = self._get_user_info(cursor, userid, assumed_status=Status.Waiting)
                num_seconds = (self.config["status_params"]["waiting"][
                                   "num_seconds"] + u.status_timestamp) - current_timestamp_in_seconds()
                return WaitingSession(u.message, num_seconds)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def get_finished_info(self, userid):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                u = self._get_user_info(cursor, userid, assumed_status=Status.Finished)
                num_seconds = (self.config["status_params"]["finished"][
                                   "num_seconds"] + u.status_timestamp) - current_timestamp_in_seconds()
                return FinishedSession(u.message, num_seconds)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def is_chat_valid(self, userid):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                try:
                    u = self._get_user_info(cursor, userid, assumed_status=Status.Chat)
                    u2 = self._get_user_info(cursor, u.partner_id, assumed_status=Status.Chat)
                    return u.room_id == u2.room_id
                except UnexpectedStatusException:
                    return False
                except StatusTimeoutException:
                    return False
                except ConnectionTimeoutException:
                    return False

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")
            return False

    def connect(self, userid):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                self._update_user(cursor, userid,
                                  connected_status=1)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def disconnect(self, userid):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                self._update_user(cursor, userid,
                                  connected_status=0)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def _ensure_not_none(self, v, exception_class):
        if v is None:
            raise exception_class()
        else:
            return v

    def pick_restaurant(self, userid, restaurant_index):
        def _get_points(scenario, agent_index, restaurant_name):
            return next(obj["utility"] for obj in scenario["agents"][agent_index]["sorted_restaurants"] if
                        obj["name"] == restaurant_name)

        def _user_finished(cursor, userid, prev_points, my_points, other_points):
            status = Status.Finished
            message = "Great, you've finished the chat! You scored {} points and your partner scored {} points.".format(
                my_points, other_points)
            self._update_user(cursor, userid, status=Status.Finished, message=message,
                              cumulative_points=prev_points + my_points)

        try:
            with self.conn:
                cursor = self.conn.cursor()
                self._update_user(cursor, userid, selected_index=restaurant_index)
                u = self._get_user_info(cursor, userid, assumed_status=Status.Chat)

                cursor.execute(
                    "SELECT name, selected_index,cumulative_points FROM ActiveUsers WHERE room_id=? AND name!=?",
                    (u.room_id, userid))
                other_userid, other_restaurant_index, other_P = self._ensure_not_none(cursor.fetchone(), BadChatException)
                P = u.cumulative_points
                scenario = self.scenarios[u.scenario_id]
                restaurant_name = scenario["restaurants"][restaurant_index]["name"]
                if u.selected_index == other_restaurant_index:
                    # Match
                    Pdelta = _get_points(scenario, u.agent_index, restaurant_name)
                    other_Pdelta = _get_points(scenario, 1 - u.agent_index, restaurant_name)
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
            raise UnexpectedStatusException()
        return

    def _assert_no_status_timeout(self, status, status_timestamp):
        N = self.config["status_params"][Status._names[status]]["num_seconds"]
        num_seconds_remaining = (N + status_timestamp) - current_timestamp_in_seconds()
        if num_seconds_remaining >= 0:
            return
        else:
            raise StatusTimeoutException()

    def _assert_no_connection_timeout(self, status, timestamp):
        if status:
            return
        else:
            N = self.config["connection_timeout_num_seconds"]
            num_seconds_remaining = (N + timestamp) - current_timestamp_in_seconds()
            if num_seconds_remaining >= 0:
                return
            else:
                raise ConnectionTimeoutException()

    def _update_user(self, cursor, userid, **kwargs):
        if "status" in kwargs:
            kwargs["status_timestamp"] = current_timestamp_in_seconds()
        if "connected_status" in kwargs:
            kwargs["connected_timestamp"] = current_timestamp_in_seconds()
        keys = sorted(kwargs.keys())
        values = [kwargs[k] for k in keys]
        set_string = ", ".join(["{}=?".format(k) for k in keys])

        cursor.execute("UPDATE ActiveUsers SET {} WHERE name=?".format(set_string), tuple(values + [userid]))

    def _get_user_info_unchecked(self, cursor, userid):
        cursor.execute("SELECT * FROM ActiveUsers WHERE name=?", (userid,))
        x = cursor.fetchone()
        u = User(self._ensure_not_none(x, NoSuchUserException))
        return u

    def _get_user_info(self, cursor, userid, assumed_status=None):
        u = self._get_user_info_unchecked(cursor, userid)
        if assumed_status is not None:
            self._validate_status_or_throw(assumed_status, u.status)
        self._assert_no_status_timeout(u.status, u.status_timestamp)
        self._assert_no_connection_timeout(u.status, u.status_timestamp)
        return u

    def submit_single_task(self, userid, user_input):
        def _complete_task_and_wait(cursor, userid, num_finished):
            message = "Great, you've finished {} exercises! Waiting a few seconds for a partner to chat with...".format(
                num_finished)
            self._update_user(cursor, userid, status=Status.Waiting, message=message,
                              num_single_tasks_completed=num_finished)

        def _complete_task_and_finished(cursor, userid, num_finished):
            message = "Great, you've finished {} exercises!".format(num_finished)
            self._update_user(cursor, userid, status=Status.Finished, message=message,
                              num_single_tasks_completed=num_finished)
        # todo log user input
        try:
            with self.conn:
                cursor = self.conn.cursor()
                u = self._get_user_info(cursor, userid, assumed_status=Status.SingleTask)
                if u.num_single_tasks_completed == self.config["status_params"]["single_task"]["max_tasks"] - 1:
                    _complete_task_and_finished(cursor, userid, u.num_single_tasks_completed + 1)
                else:
                    _complete_task_and_wait(cursor, userid, u.num_single_tasks_completed + 1)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def leave_room(self, userid):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                u = self._get_user_info(cursor, userid, assumed_status=Status.Chat)
                message = "You have left the room. Waiting for a new chat..."
                partner_message = "Your partner has left the room! Waiting for a new chat..."
                self._end_chat_and_transition_to_waiting(cursor, userid, u.partner_id, message=message,
                                                         partner_message=partner_message)

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def attempt_join_room(self, userid):
        def _get_other_waiting_users(cursor, userid):
            # NOTE: we could try to handle single task as another waiting mode
            #       we could also even interrupt single task mode (requires e.g. periodic polling by client during SingleTask mode)
            cursor.execute("SELECT name FROM ActiveUsers WHERE name!=? AND status=?", (userid, Status.Waiting))
            userids = [r[0] for r in cursor.fetchall()]
            return userids

        def _get_max_room_id(cursor):
            cursor.execute("SELECT MAX(room_id) FROM ActiveUsers", ())
            return cursor.fetchone()[0]

        try:
            with self.conn:
                cursor = self.conn.cursor()
                u = self._get_user_info(cursor, userid, assumed_status=Status.Waiting)
                others = _get_other_waiting_users(cursor, userid)
                if len(others) > 0:
                    scenario_id = random.choice(self.scenarios.keys())
                    other_userid = random.choice(others)
                    next_room_id = _get_max_room_id(cursor) + 1
                    my_agent_index = random.choice([0, 1])
                    self._update_user(cursor, other_userid,
                                      status=Status.Chat,
                                      room_id=next_room_id,
                                      partner_id=userid,
                                      scenario_id=scenario_id,
                                      agent_index=1 - my_agent_index,
                                      selected_index=-1,
                                      message="")
                    self.conn.commit()
                    self._update_user(cursor, userid,
                                      status=Status.Chat,
                                      room_id=next_room_id,
                                      partner_id=other_userid,
                                      scenario_id=scenario_id,
                                      agent_index=my_agent_index,
                                      selected_index=-1,
                                      message="")
                    self.conn.commit()
                    return next_room_id
                else:
                    return None
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")
