from flask import current_app as app
import random
import sqlite3
import time


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
            cursor.execute('''INSERT OR IGNORE INTO ActiveUsers VALUES (?,?,?,?)''', (username, 0, 0, ''))

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
                    r = random.sample(empty_rooms, 1)
                    room = r[0]
                    cursor.execute('''UPDATE Chatrooms SET participants=2,scenario=? WHERE number=?''',
                                   (scenario_id, room))
                else:
                    # otherwise, find the max room number and create a new room with number = max + 1
                    # (or 1 if it's the first room)
                    cursor.execute('''SELECT MAX(number) FROM Chatrooms''')
                    r = cursor.fetchone()
                    if r is None or r[0] is None:
                        room = 1
                    else:
                        room = r[0] + 1
                    cursor.execute('''INSERT INTO Chatrooms VALUES (?,2,?)''', (room, scenario_id))
                return room

        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def leave_room(self, username, room):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute("UPDATE Chatrooms SET participants = participants - 1 WHERE number=?", (room,))
                cursor.execute("UPDATE ActiveUsers SET room=0,agentid=0,partner='' WHERE name=?", (username,))
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")

    def select_restaurant(self, username, partner, scenario_id, outcome):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                # see if the other user has already submitted an outcome for this chat
                cursor.execute('''SELECT outcome FROM Outcomes WHERE agent1=? AND agent2=? AND scenario=? ORDER BY time DESC''', (partner, username, scenario_id))
                stored_outcome = cursor.fetchone()
                if stored_outcome:
                    if stored_outcome != outcome:
                        # do something - the two agents selected different restaurants
                        pass
                else:
                    cursor.execute('''INSERT INTO Outcomes VALUES (?,?,?,?,?)''', (username, partner, scenario_id,
                                                                                   outcome, int(time.time()*1000)))
        except sqlite3.IntegrityError:
            print("WARNING: Rolled back transaction")


