from __future__ import with_statement
import random
import sqlite3
import app.main.utils
from flask import current_app as app


class BackendConnection(object):
    def __init__(self, location, scenario_ids):
        self.conn = sqlite3.connect(location)
        self.scenario_ids = scenario_ids

    def close(self):
        self.conn.close()
        self.conn = None

    def create_user_if_necessary(self, username):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO ActiveUsers VALUES (?,?,?,?,?)''', (username, 0, 0, '',0))

    def pick_restaurant_and_check_match(self, room, agent_number, restaurant_id):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                selected_column = "selected_restaurant_{}".format(agent_number)
                cursor.execute("UPDATE Chatrooms SET {} = ? WHERE number=?".format(selected_column), (restaurant_id, room))
                cursor.execute("SELECT selected_restaurant_1,selected_restaurant_2 FROM Chatrooms WHERE number=?", (room,))
                entry = cursor.fetchone()
                app.logger.debug(entry)
                if entry[0] is not None and entry[1] is not None and entry[0] == entry[1]:
                    return True, entry[0]
                else:
                    return False, None
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

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
                app.logger.debug(user_entry)
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

