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
        wait = route_to_task()
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
def waiting():
    global ctr
    while ctr < constants.WAITING_TIME:
        time.sleep(1)
        ctr += 1
        wait = route_to_task()
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


def route_to_task():
    conn = sqlite3.connect(constants.CHAT_ROOM_DB)
    cursor = conn.cursor()
    current_user = (session.get('name'),)
    # see if the current user has already been paired
    cursor.execute('''SELECT * FROM ActiveUsers WHERE name=?''', current_user)
    user_row = cursor.fetchone()
    if user_row[1] != 0:
        session['room'] = user_row[1]
        return False

    cursor.execute('''SELECT name FROM ActiveUsers WHERE room = 0 AND name!=?''', current_user)
    unpaired_users = cursor.fetchall()

    if unpaired_users:
        paired_user = random.sample(unpaired_users, 1)[0]
        room = assign_room(current_user, paired_user)
        cursor.execute('''UPDATE ActiveUsers SET room=? WHERE name=?''', (room, paired_user[0]))
        cursor.execute('''UPDATE ActiveUsers SET room=? WHERE name=?''', (room, current_user[0]))
        conn.commit()
        conn.close()
        session['room'] = room
        return False
    else:
        return True


def assign_room(participant1, participant2):
    conn = sqlite3.connect(constants.CHAT_ROOM_DB)
    cursor = conn.cursor()
    cursor.execute('''SELECT number FROM Chatrooms WHERE participants = 0''')
    empty_rooms = cursor.fetchall()

    if empty_rooms:
        room = random.sample(empty_rooms,1)[0]
        cursor.execute('''UPDATE Chatrooms SET player1=?,player2=?,participants=2 WHERE number=?''',
                       (participant1, participant2, room))
    else:
        cursor.execute('''SELECT MAX(number) FROM Chatrooms''')
        room = cursor.fetchone()
        if room[0] is None:
            room = (1,)
        else:
            room = (room[0]+1,)
        cursor.execute('''INSERT INTO Chatrooms VALUES (?,?,?,2)''',
                       (room[0], participant1[0], participant2[0]))
    conn.commit()
    conn.close()

    return room[0]
