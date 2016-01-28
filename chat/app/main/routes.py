from flask import session, redirect, url_for, render_template, request, jsonify
from flask import current_app as app
from . import main
import time
from .utils import get_backend, generate_outcome_key, UserChatSession
from .events import write_outcome
import copy

pairing_wait_ctr = 0
validation_wait_ctr = 0

def userid():
    return request.sid

# todo try and use one connection everywhere, put code to find unpaired users into single function
@main.route('/', methods=['GET', 'POST'])
def chat():
    """Chat room. The user's name and room must be stored in
    the session."""
    chat_session = session.get('chat_session', None)

    if chat_session:
        presentation_config = app.config["user_params"]["chat_presentation_config"]
        return render_template('chat.html', 
                               room=chat_session.room, 
                               scenario=chat_session.scenario, 
                               agent=chat_session.agent_info, 
                               config=presentation_config)
    else:
        pass
        #TODO handle error

@main.route('/')
# todo: something like this needs to happen when a single task is submitted, too
def waiting():
    global pairing_wait_ctr
    while pairing_wait_ctr < app.config["user_params"]["waiting_time_seconds"]:
        time.sleep(1)
        pairing_wait_ctr += 1
        found_room = find_room_if_possible(userid())
        if found_room:
            pairing_wait_ctr = 0
            return redirect(url_for('.chat'))
        else:
            return redirect(url_for('.waiting'))
    pairing_wait_ctr = 0
    return render_template('single_task.html')


def add_new_user(username):
    backend = get_backend()
    backend.create_user_if_necessary(username)


def find_room_if_possible(username):
    backend = get_backend()
    room, scenario_id, agent_index, partner_id = backend.find_room_for_user_if_possible(username)
    if room:
        session["chat_session"] = UserChatSession(room, agent_index, scenario_id, app.config["user_params"]["scenario_time_seconds"], userid(), partner_id)
        return True
    return False
