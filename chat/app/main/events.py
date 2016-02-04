from flask import session, request
from flask import current_app as app
from flask.ext.socketio import emit, join_room, leave_room
from .. import socketio
from datetime import datetime
from .utils import get_backend
from .routes import userid

date_fmt = '%m-%d-%Y:%H-%M-%S'


@socketio.on('check_status_change', namespace='/chat')
def check_status_change(data):
    backend = get_backend()
    current_status = data['current_status']

    new_status = backend.get_status(userid())
    if current_status == new_status:
        return {'status_change':False}
    else:
        return {'status_change':True}


@socketio.on('submit_task', namespace='/chat')
def submit_task(data):
    backend = get_backend()
    backend.submit_singe_task(userid(), data) # todo maybe need to unpack the return values first before passing


@socketio.on('joined', namespace='/chat')
def joined(message):
    """Sent by clients when they enter a room.
    A status message is broadcast to all people in the room."""
    start_chat()
    join_room(session["room"])
    emit_message_to_partner("Your partner has entered the room.", status_message=True)


@socketio.on('text', namespace='/chat')
def text(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    msg = message['msg']
    write_to_file(message['msg'])
    emit_message_to_self("You: {}".format(msg))
    emit_message_to_partner("Partner: {}".format(msg))


@socketio.on('pick', namespace='/chat')
def pick(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    backend = get_backend()
    restaurant_id = int(message['restaurant'])
    room = session["room"]

    restaurant, is_match = backend.pick_restaurant(userid(), restaurant_id)
    if is_match:
        emit_message_to_chat_room("Both users have selected restaurant: \"{}\"".format(restaurant), status_message=True)
        emit('endchat',
             {'message':"You've completed this task! Redirecting you..."},
             room=room)
    else:
        emit_message_to_partner("Your friend has selected restaurant: \"{}\"".format(restaurant["name"]), status_message=True)
        emit_message_to_self("You selected restaurant: \"{}\"".format(restaurant["name"]), status_message=True)
    write_outcome(restaurant)


@socketio.on('left_room', namespace='/chat')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    room = session["room"]

    leave_room(room)
    backend = get_backend()
    backend.disconnect(userid())
    end_chat()
    emit('endchat',
         {'message':'Your friend has left or been disconnected. Redirecting you...'},
         room=room, include_self=False)


@socketio.on('user_disconnected', namespace='/chat')
def disconnect():
    """
    Called when user disconnects from a state other than Status.Chat
    :return: No return value
    """
    backend = get_backend()
    backend.disonnect(userid())


def emit_message_to_self(message, status_message=False):
    timestamp = datetime.now().strftime('%x %X')
    left_delim = "<" if status_message else ""
    right_delim = ">" if status_message else ""
    emit('message', {'msg': "[{}] {}{}{}".format(timestamp, left_delim, message, right_delim)}, room=request.sid)


def emit_message_to_chat_room(message, status_message=False):
    timestamp = datetime.now().strftime('%x %X')
    left_delim = "<" if status_message else ""
    right_delim = ">" if status_message else ""
    emit('message', {'msg': "[{}] {}{}{}".format(timestamp, left_delim, message, right_delim)}, room=session["room"])


def emit_message_to_partner(message, status_message=False):
    timestamp = datetime.now().strftime('%x %X')
    left_delim = "<" if status_message else ""    
    right_delim = ">" if status_message else ""
    emit('message', {'msg': "[{}] {}{}{}".format(timestamp, left_delim, message, right_delim)}, exclude_self = True)


def start_chat():
    chat_dict = get_backend().get_chat_info(userid()).to_dict()

    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(session["room"])), 'a+')
    outfile.write("%s\t%s\tUser %s\tjoined\n" % (datetime.now().strftime(date_fmt),
                                            chat_dict["scenario"]["uuid"],
                                            str(chat_dict["agent_index"])))
    outfile.close()


def end_chat():
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(session["room"])), 'a+')
    outfile.write("%s\t%s\n" % (datetime.now().strftime(date_fmt), app.config["user_params"]["CHAT_DELIM"]))
    outfile.close()


def write_to_file(message):
    chat_dict = get_backend().get_chat_info(userid()).to_dict()
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(session["room"])), 'a+')
    outfile.write("%s\t%s\tUser %s\t%s\n" %
                  (datetime.now().strftime(date_fmt), chat_dict["scenario"]["uuid"],
                   str(chat_dict["agent_index"]), message))
    outfile.close()


def write_outcome(name):
    chat_dict = get_backend().get_chat_info(userid()).to_dict()
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(session["room"])), 'a+')
    outfile.write("%s\t%s\tUser %s\tSelected restaurant:\t%s\n" %
                  (datetime.now().strftime(date_fmt), chat_dict["scenario"]["uuid"], chat_dict["agent_index"], name))
