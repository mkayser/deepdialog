__author__ = 'mkayser'
from flask import g, session, redirect, url_for, render_template, request
from flask import current_app as app
from .backend import BackendConnection


def compute_agent_score(agent, restaurant):
    pr = restaurant["price_range"]
    c = restaurant["cuisine"]

    sf = agent["spending_func"]
    cf = agent["cuisine_func"]

    pr_points = next(obj["utility"] for obj in sf if obj["price_range"]==pr)
    c_points = next(obj["utility"] for obj in cf if obj["cuisine"]==c)

    return pr_points + c_points

class FinishedSession(object):
    def __init__(self, message, num_seconds):
        self.message = message
        self.num_seconds = num_seconds
        # TODO: How to ensure that user doesn't see finished screen when returning for a second (third, etc.) task
        # One way is to have a new socketIO event that flags that the user has submitted the MTurk code

class WaitingSession(object):
    def __init__(self, message, num_seconds):
        self.message = message
        self.num_seconds = num_seconds

class SingleTaskSession(object):
    def __init__(self, scenario, agent_index, num_seconds):
        self.scenario = scenario
        self.agent_index = agent_index
        self.agent_info = scenario[agent_index]
        self.num_seconds = num_seconds

class UserChatSession(object):
    def __init__(self, room_id, agent_index, scenario, num_seconds):
        self.room_id = room_id
        self.agent_index = agent_index
        self.scenario = scenario
        self.agent_info = scenario[agent_index]
        self.num_seconds = num_seconds

    def to_dict(self):
        return {"room": self.room_id,
                "agent_index": self.agent_index,
                "scenario": self.scenario,
                "agent_info": self.agent_info,
                "num_seconds": self.num_seconds}


def get_backend():
    backend = getattr(g, '_backend', None)
    if backend is None:
        scenario_ids = sorted(app.config["scenarios"].keys())
        backend = g._backend = BackendConnection(app.config["user_params"]["CHAT_ROOM_DB"], scenario_ids)
    return backend


def generate_outcome_key(user, partner, scenario_id):
    return (user, partner, scenario_id)


def generate_partner_key(user, partner, scenario_id):
    return (partner, user, scenario_id)
