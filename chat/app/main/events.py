from flask import g, session
from flask import current_app as app
from flask.ext.socketio import emit, join_room, leave_room
from .. import socketio
import sqlite3
from . import utils


@socketio.on('joined', namespace='/chat')
def joined(message):
    """Sent by clients when they enter a room.
    A status message is broadcast to all people in the room."""
    username = session.get("name")
    room = session.get('room')

    join_room(room)
    app.logger.debug("Testing logger: User {} has entered room {}.".format(username,room))
    emit('status', {'msg': username + ' has entered the room.'}, room=room)


@socketio.on('text', namespace='/chat')
def text(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    room = session.get('room')
    # TODO: maybe change all logging to use app.logger
    app.logger.debug("Testing logger: User {} says {} in room {}.".format(username,message["msg"],room))
    write_to_file(message['msg'])
    emit('message', {'msg': session.get('name') + ':' + message['msg']}, room=room)


@socketio.on('left', namespace='/chat')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    room = session.get('room')
    username = session.get('name')

    leave_room(room)
    backend = utils.get_backend()
    backend.leave_room(username,room)
    end_chat()
    app.logger.debug("Testing logger: User {} left room {}.".format(username,room))
    emit('status', {'msg': session.get('name') + ' has left the room or been disconnected. Please '
                                                 'click the link below to find a new opponent.'}, room=room)


def end_chat():
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(session.get('room'))), 'a+')
    outfile.write(app.config["user_params"]["CHAT_DELIM"]+"\n")
    outfile.close()


def write_to_file(message):
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(session.get('room'))), 'a+')
    outfile.write("%s\t%s\n" % (session.get('name'), message))
    outfile.close()


