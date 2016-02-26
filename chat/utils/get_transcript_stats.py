__author__ = 'anushabala'

from argparse import ArgumentParser
import json
import re
import os
import sys
import shutil
import codecs

user_regex = r'User ([0-9])'
restaurant_regex = 'Selected restaurant ([0-9]+): (.*)'
SELECT_RESTAURANT = 'Selected restaurant:'
user_id_regex = r'User ([0-9]) has user ID (.*)'
NO_OUTCOME = "NO_OUTCOME"
TOO_SHORT = "TOO_SHORT"
SHORT = "SHORT"
BOTH = "BOTH"
NEITHER = "NEITHER"
ONE = "ONE"


def load_scenarios(scenarios_file):
    json_scenarios = json.load(open(scenarios_file, 'r'), encoding='utf-8')
    return {scenario["uuid"]:scenario for scenario in json_scenarios}


def parse_transcript(transcript_file):
    infile = open(transcript_file, 'r')
    transcript = {}
    choices = {}
    ids = {}
    dialogue = []
    transcript["ids"] = ids
    transcript["choices"] = choices
    transcript["dialogue"] = dialogue

    for line in infile.readlines():
        line = line.strip().split("\t")
        if line[1] == '---' or (len(line) == 4 and line[-1] == 'joined'):
            continue
        if "scenario" not in transcript.keys():
            scenario_id = line[1]
            transcript["scenario"] = scenario_id

        id_match = re.match(user_id_regex, line[2])
        if id_match:
            agent_num = int(id_match.group(1))
            ids[agent_num] = id_match.group(2)
        else:
            user_match = re.match(user_regex, line[2])
            agent_num = int(user_match.group(1))
            if len(line) == 5:
                choice_match = re.match(restaurant_regex, " ".join(line[3:]))
                if choice_match:
                    choices[agent_num] = (choice_match.group(1), choice_match.group(2))
                elif line[3] == SELECT_RESTAURANT:
                    choices[agent_num] = (-1, line[4])
            else:
                try:
                    dialogue.append((agent_num, line[3]))
                except IndexError:
                    continue

    transcript["outcome"] = NO_OUTCOME
    if 0 in choices.keys() and 1 in choices.keys():
        if choices[0][1] == choices[1][1]:
            transcript["outcome"] = choices[0]

    infile.close()
    return transcript


def is_transcript_valid(transcript):
    if transcript["outcome"] == NO_OUTCOME:
        return False, NO_OUTCOME
    return True, None


def is_transcript_short(transcript):
    user_0_count = len([d for d in transcript["dialogue"] if d[0] == 0])
    user_1_count = len([d for d in transcript["dialogue"] if d[0] == 1])

    if user_0_count < 1 or user_1_count < 1:
        return True, TOO_SHORT

    if user_0_count < 2 or user_1_count < 2:
        return True, SHORT

    return False, None


def user_picked_optimal(user_num, transcript, scenarios):
    scenario = scenarios[transcript["scenario"]]
    idx, name = transcript["choices"][user_num]
    sorted_restaurants = scenario["agents"][user_num]["sorted_restaurants"]
    max_utility = sorted_restaurants[0]["utility"]
    try:
        choice_utility = next(obj["utility"] for obj in scenario["agents"][user_num]["sorted_restaurants"] if
                              obj["name"] == name)
    except StopIteration:
        choice_utility = 0
    if choice_utility == max_utility or sorted_restaurants[2]["name"] == name:
        return True

    return False


def write_preferences(open_file, scenario):
    user0_prefs = scenario["agents"][0]
    user1_prefs = scenario["agents"][1]
    open_file.write("User 0 preferences: %s\t%s\n" %
                    ("-".join([str(x) for x in user0_prefs["spending_func"][0]["price_range"]]),
                    ", ".join([c["cuisine"] for c in user0_prefs["cuisine_func"]])))
    open_file.write("User 1 preferences: %s\t%s\n" %
                    ("-".join([str(x) for x in user1_prefs["spending_func"][0]["price_range"]]),
                    ", ".join([c["cuisine"] for c in user1_prefs["cuisine_func"]])))


def write_available_restaurants(open_file, scenario):
    restaurants = scenario["restaurants"]
    for r in restaurants:
        open_file.write("%s\t%s\t%s\n" % (r["name"], r["cuisine"], "-".join([str(x) for x in r["price_range"]])))

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--scenarios", type=str, default='../scenarios.json', help='File containing JSON scenarios')
    parser.add_argument("--transcripts", type=str, default='../transcripts', help='Directory containing chat transcripts')
    parser.add_argument("--out_dir", type=str, default='../transcripts_with_prefs', help='Directory to write output transcripts to')
    args = parser.parse_args()
    scenarios = load_scenarios(args.scenarios)
    out_dir = args.out_dir

    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)

    os.makedirs(out_dir)


    ctr = 0
    invalid = {NO_OUTCOME: 0, TOO_SHORT: 0, SHORT: 0}
    optimal_choice = {BOTH: 0, NEITHER: 0, ONE: 0}

    for name in os.listdir(args.transcripts):
        f = os.path.join(args.transcripts, name)
        transcript = parse_transcript(f)

        valid, reason = is_transcript_valid(transcript)
        if not valid:
            invalid[reason] += 1
        else:
            out = os.path.join(out_dir, name)
            shutil.copyfile(f, out)
            out_file = codecs.open(out, mode='a', encoding='utf-8')
            out_file.write("\nChat Information:\n\n")
            write_preferences(out_file, scenarios[transcript["scenario"]])
            out_file.write("\n")
            write_available_restaurants(out_file, scenarios[transcript["scenario"]])
            out_file.write("\n")

            short, reason = is_transcript_short(transcript)
            if short:
                invalid[reason] += 1

            user_0_optimal = user_picked_optimal(0, transcript, scenarios)
            user_1_optimal = user_picked_optimal(1, transcript, scenarios)

            if user_0_optimal and user_1_optimal:
                optimal_choice[BOTH] += 1
            elif user_0_optimal or user_1_optimal:
                optimal_choice[ONE] += 1
            else:
                optimal_choice[NEITHER] += 1

            if user_0_optimal:
                out_file.write("User 0 selected their optimal choice (or something close).\n")
            if user_1_optimal:
                out_file.write("User 1 selected their optimal choice (or something close).\n")

            out_file.close()
        ctr += 1



    print optimal_choice
    print invalid
