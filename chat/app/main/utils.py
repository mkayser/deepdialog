__author__ = 'mkayser'
from flask import g, session, redirect, url_for, render_template, request
from flask import current_app as app
from .backend import BackendConnection


def compute_agent_score(agent, restaurant):
    pr = restaurant["price_range"]
    c = restaurant["cuisine"]
    
    sf = agent["spending_func"]
    cf = agent["cuisine_func"]

    pr_points = next(points for pr_,points in sf if pr_==pr)
    c_points = next(points for c_,points in cf if c_==c)
    
    return pr_points + c_points

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
