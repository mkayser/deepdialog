from flask import session
from flask.ext.socketio import emit, join_room, leave_room
from .. import socketio
from .. import constants
import sqlite3


@socketio.on('joined', namespace='/chat')
def joined(message):
    """Sent by clients when they enter a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    join_room(room)
    emit('status', {'msg': session.get('name') + ' has entered the room.'}, room=room)


@socketio.on('text', namespace='/chat')
def left(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    room = session.get('room')
    write_to_file(message['msg'])
    emit('message', {'msg': session.get('name') + ':' + message['msg']}, room=room)


@socketio.on('left', namespace='/chat')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    leave_room(room)
    update_db()
    end_chat()
    emit('status', {'msg': session.get('name') + ' has left the room or been disconnected. Please '
                                                 'click the link below to find a new opponent.'}, room=room)


def end_chat():
    outfile = open('%s/ChatRoom_%s' % (constants.CHAT_DIRECTORY, str(session.get('room'))), 'a+')
    outfile.write(constants.CHAT_DELIM+"\n")
    outfile.close()


def write_to_file(message):
    outfile = open('%s/ChatRoom_%s' % (constants.CHAT_DIRECTORY, str(session.get('room'))), 'a+')
    outfile.write("%s\t%s\n" % (session.get('name'), message))
    outfile.close()


def update_db():
    conn = sqlite3.connect(constants.CHAT_ROOM_DB)
    c = conn.cursor()
    c.execute("UPDATE Chatrooms SET participants = participants - 1 WHERE number=?", session.get('room'))
    c.execute("UPDATE ActiveUsers SET room=0 WHERE name=?", session.get('name'))
    conn.commit()
    conn.close()
