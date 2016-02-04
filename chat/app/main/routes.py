from flask import session, redirect, url_for, render_template, request, jsonify
from flask import current_app as app
from . import main
import time
from .utils import get_backend, UserChatSession
import uuid

pairing_wait_ctr = 0
validation_wait_ctr = 0


def set_or_get_userid():
    if session["sid"]:
        return userid()
    session["sid"] = request.cookies.get(app.session_cookie_name)
    if not session["sid"]:
        session["sid"] = str(uuid.uuid4().hex)

    get_backend().create_user_if_necessary(session["sid"])
    return session["sid"]


def userid():
    return session["sid"]


@main.route('/', methods=['GET', 'POST'])
def main():
    """Chat room. The user's name and room must be stored in
    the session."""

    set_or_get_userid()
    # clear all chat session data
    # session["chat_session"] = None

    backend = get_backend()

    status = backend.get_status()

    if status == "waiting":
        waiting_info = backend.get_waiting_info(userid())
        return render_template('waiting.html',
                               seconds_until_expiration = waiting_info['seconds_until_expiration'],
                               waiting_message = waiting_info['waiting_message'])
    elif status == "single_task":
        single_task_info = backend.get_single_task_info(userid())
        return render_template('single_task.html',
                               scenario = single_task_info['scenario'])
    elif status == "finished":
        finished_info = backend.get_finished_info(userid())
        return render_template('finished.html',
                               mturk_code = finished_info['mturk_code'],
                               finished_message = finished_info['finished_message'])
    else:
        chat_info = backend.get_chat_info(userid())
        chat_dict = chat_info.to_dict()
        presentation_config = app.config["user_params"]["chat_presentation_config"]
        session["room"] = chat_dict["room"]
        return render_template('chat.html',
                               room = chat_dict["room"],
                               scenario = chat_dict["scenario"],
                               agent = chat_dict["agent_info"],
                               num_seconds = chat_dict["num_seconds"],
                               config=presentation_config)
