from flask import session, redirect, url_for, render_template, request, jsonify
from flask import current_app as app
from . import main
from .forms import LoginForm, RestaurantForm
import time
from .utils import get_backend, generate_outcome_key, compute_agent_score
from .events import write_outcome
import copy

pairing_wait_ctr = 0
validation_wait_ctr = 0


# todo try and use one connection everywhere, put code to find unpaired users into single function
@main.route('/', methods=['GET', 'POST'])
def index():
    """"Login form to enter a room."""
    form = LoginForm()
    if form.validate_on_submit():
        session['name'] = form.name.data
        add_new_user(session["name"])
        room, scenario_id = find_room_if_possible(session["name"])
        if room:
            return redirect(url_for('.chat'))
        else:
            return redirect(url_for('.waiting'))
    elif request.method == 'GET':
        form.name.data = session.get('name', '')
    return render_template('index.html', form=form)

@main.route('/chat', methods=['GET', 'POST'])
def chat():
    """Chat room. The user's name and room must be stored in
    the session."""
    name = session.get('name', None)
    room = session.get('room', None)
    agent_number = session.get('agent_number')
    scenario_id = session.get('scenario_id', None)
    partner = session.get('partner')

    form=RestaurantForm()
    scenario = None
    if scenario_id:
        scenario = app.config["scenarios"][scenario_id]
        scenario_num_seconds = app.config["user_params"]["scenario_time_seconds"]
        agent = scenario["agents"][agent_number-1]
        sorted_restaurants = sorted(scenario["restaurants"], key=lambda x: -compute_agent_score(agent, x))
        form.restaurants.choices = list(enumerate([i["name"] for i in scenario["restaurants"]]))
        config = app.config["user_params"]["chat_presentation_config"]

    app.logger.debug("Testing logger: chat requested.")
    if name is None or room is None or scenario_id is None:
        return redirect(url_for('.index'))
    else:
        return render_template('chat.html', name=name, room=room, scenario=scenario, agent_number=agent_number, form=form,
                               partner=partner, sorted_restaurants=sorted_restaurants, agent=agent, scenario_num_seconds=scenario_num_seconds,
                               config=config)

# def compute_dollar_rating(price_range, dollar_ratings):
#     for pr,rating in dollar_ratings:
#         if pr==price_range:
#             return rating
#     raise Exception("No dollar rating found")

# def compute_cuisine_rating(utility, cuisine_ratings):
#     for u,rating in cuisine_ratings:
#         if u>=utility:
#             return rating
#     raise Exception("No dollar rating found")

# # TODO: change this hacky way of getting stars/etc. information 
# def augment_agent_info(agent, ratings_info):
#     a = copy.deepcopy(agent)
#     for o in a["spending_func"]:
#         o["dollar_rating"] = compute_dollar_rating(o["price_range"], ratings_info["dollar_ratings"])
#     for o in a["cuisine_func"]:
#         o["cuisine_rating"] = compute_cuisine_rating(o["utility"], ratings_info["cuisine_ratings"])
#     return a

@main.route('/_validate', methods=['POST'])
def reset():
    app.logger.debug("Resetting outcomes...")
    global validation_wait_ctr
    validation_wait_ctr = 0
    name = session.get('name', None)
    partner = session.get('partner')
    scenario_id = session.get('scenario_id', None)
    key = generate_outcome_key(name, partner, scenario_id)
    app.config["outcomes"][key] = -1
    return jsonify(completed=True)


@main.route('/_validate', methods=['GET'])
def validate_and_compute_score():
    global validation_wait_ctr
    outcome = request.args.get('outcome', -1, type=int)
    app.logger.debug("%d" % (outcome))

    name = session.get('name', None)
    agent_number = session.get('agent_number')
    scenario_id = session.get('scenario_id', None)
    scenario = app.config["scenarios"][scenario_id]
    partner = session.get('partner')
    restaurant = scenario["restaurants"][outcome]
    backend = get_backend()

    success = 0
    score = 0
    if validation_wait_ctr < app.config["user_params"]["waiting_time_seconds"]:
        time.sleep(2)
        validation_wait_ctr += 1
        success = backend.select_restaurant(name, partner, scenario_id, outcome)
        if success != -1:
            score = score_outcome(scenario, outcome, agent_number)
    else:
        if success == 0:
            success = -2 #indicates timeout

    if success == 1:
        write_outcome(outcome, *restaurant)
    return jsonify(success=success, score=score)


def score_outcome(scenario, choice, agent_number):
    selected_restaurant = scenario["restaurants"][choice]
    score = 0
    utility = scenario["agents"][agent_number-1]
    for price_range in utility["spending_func"]:
        if price_range[0] == selected_restaurant[2]:
            score += price_range[1]
    for cuisine in utility["cuisine_func"]:
        if cuisine[0] == selected_restaurant[1]:
            score += cuisine[1]

    return score


@main.route('/single_task')
# todo: something like this needs to happen when a single task is submitted, too
def waiting():
    name = session.get('name', None)
    global pairing_wait_ctr
    while pairing_wait_ctr < app.config["user_params"]["waiting_time_seconds"]:
        time.sleep(1)
        pairing_wait_ctr += 1
        room, scenario_id = find_room_if_possible(name)
        if room:
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
    room, scenario_id, agent_number, partner = backend.find_room_for_user_if_possible(username)
    app.logger.debug("User %s has agent ID %d" % (username, agent_number))
    if room:
        session["room"] = room
        session["scenario_id"] = scenario_id
        session["agent_number"] = agent_number
        session["partner"] = partner
    return (room, scenario_id)
