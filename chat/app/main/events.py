from flask import g, session, jsonify
from flask import current_app as app
from flask.ext.socketio import emit, join_room, leave_room
from .. import socketio
from . import utils
from datetime import datetime
from . import routes
from .utils import get_backend
from .routes import userid

date_fmt = '%m-%d-%Y:%H-%M-%S'


def chat_session():
    return session.get("chat_session")


@socketio.on('check_status_change', namespace='/chat')
def check_status_change(data):
    backend = get_backend(userid())
    current_status = data['current_status']

    new_status = backend.get_status()
    if current_status == new_status:
        return {'status_change':False}
    else:
        return {'status_change':True}


@socketio.on('submit_task', namespace='/chat')
def submit_task(data):
    backend = get_backend()
    backend.submit_singe_task(userid(), data) # todo maybe need to unpack the return values first before passing


def attempt_pair(userid):
    routes.find_room_if_possible(userid)
    # return chat information back to the client if paired, else return empty dictionary,


@socketio.on('joined', namespace='/chat')
def joined(message):
    """Sent by clients when they enter a room.
    A status message is broadcast to all people in the room."""
    C = chat_session()
    start_chat(C.room_id)
    join_room(C.room_id)
    app.logger.debug("Testing logger: User {} has entered room {}.".format(C.my_id, C.room))
    emit_message_to_userid("Your partner has entered the room.", C.partner_id, status_message=True)


@socketio.on('text', namespace='/chat')
def text(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    C = chat_session()
    msg = message['msg']
    write_to_file(message['msg'])
    emit_message_to_user_id("You: {}".format(msg), C.my_id)
    emit_message_to_user_id("Partner: {}".format(msg), C.partner_id)


@socketio.on('pick', namespace='/chat')
def pick(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    C = chat_session()
    restaurant_id = int(message['restaurant'])
    scenario_id = C.scenario
    username = C.my_id
    agent_number = C.agent_index
    room = C.room
    scenario = app.config["scenarios"][scenario_id]

    backend = utils.get_backend()


@socketio.on('left', namespace='/chat')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    C = chat_session()
    room = C.name
    username = C.my_id

    leave_room(room)
    backend = utils.get_backend()
    backend.leave_room(username,room)
    end_chat()
    app.logger.debug("Testing logger: User {} left room {}.".format(username,room))
    emit('endchat',
         {'message':'Your friend has left the room or been disconnected. Redirecting you to the login page...'},
         room=room, include_self=False)


def emit_message_to_user_id(message, user_id, status_message=False):
    timestamp = datetime.now().strftime('%x %X')
    left_delim = "<" if status_message else ""    
    right_delim = ">" if status_message else ""
    emit('message', {'msg': "[{}] {}{}{}".format(timestamp, left_delim, message, right_delim)}, room=user_id)


def start_chat():
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(chat_session().room)), 'a+')
    outfile.write("%s\t%s\t%s\tjoined\n" % (datetime.now().strftime(date_fmt), chat_session().scenario,
                                            chat_session().my_id))
    outfile.close()


def end_chat():
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(chat_session().room)), 'a+')
    outfile.write("%s\t%s\n" % (datetime.now().strftime(date_fmt), app.config["user_params"]["CHAT_DELIM"]))
    outfile.close()


def write_to_file(message):
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(chat_session().room)), 'a+')
    outfile.write("%s\t%s\t%s\t%s\n" %
                  (datetime.now().strftime(date_fmt), chat_session().scenario, chat_session().my_id, message))
    outfile.close()


def write_outcome(restaurant_idx, name, cuisine, price_range):
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(chat_session().room)), 'a+')
    outfile.write("%s\t%s\tSelected restaurant:\t%d\t%s\t%s\t%s\n" %
                  (datetime.now().strftime(date_fmt), chat_session().scenario, restaurant_idx, name, cuisine,
                   "\t".join([str(p) for p in price_range])))
