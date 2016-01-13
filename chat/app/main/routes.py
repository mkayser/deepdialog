from flask import session, redirect, url_for, render_template, request
from . import main
from .forms import LoginForm
from .. import constants
import sqlite3
import random
import time

ctr = 0


# todo try and use one connection everywhere, put code to find unpaired users into single function
@main.route('/', methods=['GET', 'POST'])
def index():
    """"Login form to enter a room."""
    form = LoginForm()
    if form.validate_on_submit():
        session['name'] = form.name.data
        add_new_user()
        wait = wait_or_chat()
        if not wait:
            return redirect(url_for('.chat'))
        else:
            return redirect(url_for('.waiting'))
    elif request.method == 'GET':
        form.name.data = session.get('name', '')
    return render_template('index.html', form=form)


@main.route('/chat')
def chat():
    """Chat room. The user's name and room must be stored in
    the session."""
    name = session.get('name', '')
    room = session.get('room', '')
    if name == '' or room == '':
        return redirect(url_for('.index'))
    return render_template('chat.html', name=name, room=room)


@main.route('/single_task')
# todo: something like this needs to happen when a single task is submitted, too
def waiting():
    global ctr
    while ctr < constants.WAITING_TIME:
        time.sleep(1)
        ctr += 1
        wait = wait_or_chat()
        if not wait:
            ctr = 0
            return redirect(url_for('.chat'))
        else:
            return redirect(url_for('.waiting'))
    ctr = 0
    return render_template('single_task.html')


def add_new_user():
    conn = sqlite3.connect(constants.CHAT_ROOM_DB)
    cursor = conn.cursor()
    user_data = (session.get('name'), 0)
    cursor.execute('''INSERT OR IGNORE INTO ActiveUsers VALUES (?,?)''', user_data)
    conn.commit()
    conn.close()


# Function determines whether the user has to wait or can be paired with someone. Returns true if they need to wait,
# false otherwise.

def wait_or_chat():
    conn = sqlite3.connect(constants.CHAT_ROOM_DB)
    cursor = conn.cursor()
    current_user = (session.get('name'),)
    # see if the current user has already been paired - a user is paired if their room != 0
    cursor.execute('''SELECT * FROM ActiveUsers WHERE name=?''', current_user)
    user_row = cursor.fetchone()
    if user_row[1] != 0:
        session['room'] = user_row[1]
        return False

    # find all users who aren't currently paired (and not the current user)
    cursor.execute('''SELECT name FROM ActiveUsers WHERE room = 0 AND name!=?''', current_user)
    unpaired_users = cursor.fetchall()

    # if there are any unpaired users, pick one at random and pair
    if unpaired_users:
        paired_user = random.sample(unpaired_users, 1)[0]
        room = assign_room()
        # update database to reflect that users have been assigned to these rooms
        cursor.execute('''UPDATE ActiveUsers SET room=? WHERE name=?''', (room, paired_user[0]))
        cursor.execute('''UPDATE ActiveUsers SET room=? WHERE name=?''', (room, current_user[0]))
        conn.commit()
        conn.close()
        session['room'] = room
        return False
    else:
        return True


# Assign a room to two paired users
def assign_room():
    conn = sqlite3.connect(constants.CHAT_ROOM_DB)
    cursor = conn.cursor()
    # Find any rooms with 0 participants
    cursor.execute('''SELECT number FROM Chatrooms WHERE participants = 0''')
    empty_rooms = cursor.fetchall()

    # If there are any empty (unused) rooms, assign participants to that room
    if empty_rooms:
        room = random.sample(empty_rooms, 1)[0]
        cursor.execute('''UPDATE Chatrooms SET participants=2 WHERE number=?''',
                       room)
    else:
        # otherwise, find the max room number and create a new room with number = max + 1 (or 1 if it's the first room)
        cursor.execute('''SELECT MAX(number) FROM Chatrooms''')
        room = cursor.fetchone()
        if room[0] is None:
            room = (1,)
        else:
            room = (room[0] + 1,)
        cursor.execute('''INSERT INTO Chatrooms VALUES (?,2)''', (room[0],))
    conn.commit()
    conn.close()

    return room[0]
