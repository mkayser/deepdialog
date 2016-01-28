from flask import g, session, jsonify
from flask import current_app as app
from flask.ext.socketio import emit, join_room, leave_room
from .. import socketio
from . import utils
from datetime import datetime

date_fmt = '%m-%d-%Y:%H-%M-%S'

def chat_session():
    return session.get("chat_session")


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

# TODO pick() isn't revised yet
@socketio.on('pick', namespace='/chat')
def pick(message):
    """Sent by a client when the user entered a new message.
    The message is sent to all people in the room."""
    C = chat_session()
    restaurant_id = int(message['restaurant'])
    scenario_id = session.get('scenario_id')
    scenario = app.config["scenarios"][scenario_id]

    backend = utils.get_backend()
    is_match, matching_restaurant_id = backend.pick_restaurant_and_check_match(room, agent_number, restaurant_id)
    if is_match:
        restaurant = scenario["restaurants"][matching_restaurant_id]
        emit_message_to_chat_room("Both users have selected restaurant: \"{}\"".format(restaurant["name"]), room, status_message=True)

        # Get agent info and scores
        my_agent_info = scenario["agents"][agent_number-1]
        my_name = username
        my_score = utils.compute_agent_score(my_agent_info, restaurant)

        other_agent_info = scenario["agents"][1 - (agent_number-1)]
        other_name = session.get('partner')
        other_score = utils.compute_agent_score(other_agent_info, restaurant)

        emit_message_to_chat_room("{} has received {} points.".format(my_name, my_score), room, status_message=True)
        emit_message_to_chat_room("{} has received {} points.".format(other_name, other_score), room, status_message=True)
        
        backend.update_user_points([(my_name,my_score),(other_name,other_score)])
        emit('endchat',
             {'message':'Congratulations! Your chat has now ended. You can now play again with another friend.'},
             room=room)
        return True
    else:
        restaurant = scenario["restaurants"][restaurant_id]
        # TODO: maybe change all logging to use app.logger
        app.logger.debug("Testing logger: User {} picks {} in room {}.".format(username,restaurant_id,room))
        emit_message_to_chat_room("{} has selected restaurant: \"{}\"".format(username, restaurant["name"]), room, status_message=True)
        return False


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
    emit('endchat',
         {'message':'Your friend has left the room or been disconnected. Redirecting you to the login page...'},
         room=room, include_self=False)


def emit_message_to_user_id(message, user_id, status_message=False):
    timestamp = datetime.now().strftime('%x %X')
    left_delim = "<" if status_message else ""    
    right_delim = ">" if status_message else ""
    emit('message', {'msg': "[{}] {}{}{}".format(timestamp, left_delim, message, right_delim)}, room=user_id)


# TODO logging to file is not revised to use the correct ID's in place of name
def start_chat():
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(session.get('room'))), 'a+')
    outfile.write("%s\t%s\t%s\tjoined\n" % (datetime.now().strftime(date_fmt), session.get('scenario_id'),
                                            session.get('name')))
    outfile.close()


def end_chat():
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(session.get('room'))), 'a+')
    outfile.write("%s\t%s\n" % (datetime.now().strftime(date_fmt), app.config["user_params"]["CHAT_DELIM"]))
    outfile.close()


def write_to_file(message):
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(session.get('room'))), 'a+')
    outfile.write("%s\t%s\t%s\t%s\n" %
                  (datetime.now().strftime(date_fmt), session.get('scenario_id'), session.get('name'), message))
    outfile.close()


def write_outcome(restaurant_idx, name, cuisine, price_range):
    outfile = open('%s/ChatRoom_%s' % (app.config["user_params"]["CHAT_DIRECTORY"], str(session.get('room'))), 'a+')
    outfile.write("%s\t%s\tSelected restaurant:\t%d\t%s\t%s\t%s\n" %
                  (datetime.now().strftime(date_fmt), session.get('scenario_id'), restaurant_idx, name, cuisine,
                   "\t".join([str(p) for p in price_range])))
