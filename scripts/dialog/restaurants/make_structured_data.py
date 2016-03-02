import sqlite3
import re
import json
import argparse
import sys
import glob
from treebank_tokenizer import TreebankWordTokenizer
import itertools

DEBUG=0
tokenizer = TreebankWordTokenizer()

class EventTypes(object):
    Selection="Selection"
    Utterance="Utterance"
    Entrance="Entrance"

class ChatSession(object):
    def __init__(self, transcript_file, scenarios):
        def _get_user_num(s):
            if s=="User 0":
                return 0
            elif s=="User 1":
                return 1
            else:
                raise Exception("Unexpected user num: {}".format(s))

        self.user_ids = [None,None]
        self.events = []
        self.scenario= None

        with open(transcript_file,"r") as fin:
            for line in fin:
                tokens = [t.strip() for t in line.split("\t")]
                if len(tokens)==2:
                    assert(tokens[1]=="---")
                else:
                    if self.scenario is None:
                        self.scenario = scenarios[tokens[1]]

                    if len(tokens)>3:
                        uid = _get_user_num(tokens[2])
                    timestamp = tokens[0]
                        
                    if len(tokens)==5:
                        assert tokens[3].startswith("Selected restaurant"), "Expected restaurant selection in file {} in string: {}".format(transcript_file, tokens[3])
                        e = {"type":EventTypes.Selection, "timestamp":timestamp, "user":uid, "selection":tokens[4]}
                        self.events.append(e)
                    elif len(tokens)==4 and tokens[3]=="joined":
                        e = {"type":EventTypes.Entrance, "timestamp":timestamp, "user":uid}
                        self.events.append(e)                        
                    elif len(tokens)==4:
                        e = {"type":EventTypes.Utterance, "timestamp":timestamp, "user":uid, "utterance":tokens[3]}
                        self.events.append(e)
                    elif len(tokens)==3:
                        m=re.match(r'User (\d+) has user ID (\S+)', tokens[2])
                        if m:
                            uindex = int(m.group(1))
                            uid = m.group(2)
                            self.user_ids[uindex] = uid
                        else:
                            raise Exception("Unexpected 3-token transcript line in file {}: {}".format(transcript_file, line))
                    else:
                        raise Exception("Unexpected transcript line with {} tokens in file {}: {}".format(len(tokens), transcript_file, line))
    def as_dict(self):
        return {"scenario_uuid":self.scenario["uuid"], "events":self.events}
                        

def import_table_as_list_of_dict(conn,table_name):
    def _make_dict(colnames, row):
        return {k:v for k,v in zip(colnames, row)}
    with conn:
        c = conn.cursor()
        c.execute("SELECT * FROM {}".format(table_name), ())
        rows = c.fetchall()
        c.execute("PRAGMA table_info('{}')".format(table_name),())
        colinfo = c.fetchall()
        colnames = [col[1] for col in colinfo]
        return [_make_dict(colnames, r) for r in rows]
        
def load_json_from_file(fname):
    with open(fname,"r") as fin:
        return json.load(fin)


def write_json_to_file(obj, fname):
    with open(fname,"w") as fout:
        json.dump(obj,fout,indent=4,sort_keys=True)

def write_chat_sessions_file(sessions, fname):
    S = [s.as_dict() for s in sessions]
    write_json_to_file(S, fname)

def write_merged_scenarios_file(scenarios, fname):
    write_json_to_file(scenarios, fname)


def tokenize(s):
    return " ".join(tokenizer.tokenize(s.encode('utf-8'))).lower()

def gen_seq2seq_input(spending_func, cuisine_func, sorted_restaurants):
    def _num(n, c):
        return " ".join([c for i in xrange(n)])
    def _tok(s):
        return tokenize(s)
    for sfe in spending_func:
        p = sfe["price_rating"]
        u = sfe["utility"]
        yield "[ PRICE {} UTILITY {} ]".format(_num(p,"$"), _num(u,"X"))
    for cfe in cuisine_func:
        c = cfe["cuisine"]
        u = cfe["utility"]
        yield "[ CUISINE {} UTILITY {} ]".format(_tok(c), _num(u,"X"))
    for r in sorted_restaurants:
        n = r["name"]
        p = r["price_rating"]
        c = r["cuisine"]
        u = r["utility"]
        yield "[ RESTAURANT NAME {} PRICE {} CUISINE {} UTILITY {} ]".format(_tok(n), _num(p,"$"), _tok(c), _num(u,"X"))
    yield "START"
        

def gen_seq2seq_conversation(events, myid):
    for e in events:
        uid = e["user"]
        pair = [None, None]
        assert(uid in [0,1])
        one_if_me = 1 - abs(myid-uid)
        if e["type"] == EventTypes.Selection:
            pair[one_if_me] = "SELECT NAME {}".format(tokenize(e["selection"]))
        elif e["type"] == EventTypes.Entrance:
            pair = None
        elif e["type"] == EventTypes.Utterance:
            pair[one_if_me] = "SAY {}".format(tokenize(e["utterance"]))
        if pair:
            yield pair
        

def coalesce_pairs(pairs):
    output_pairs = []
    current_pair = None
    for p in pairs:
        _in = p[0]
        _out = p[1]
        if _in is not None:
            if current_pair is None:
                current_pair = [_in,None]
            elif current_pair[0] is None:
                raise Exception("Shouldn't happen")
            elif current_pair[1] is None:
                current_pair[0] = current_pair[0] + " " + _in
            else:
                output_pairs.append(current_pair)
                current_pair = [_in, None]
        if _out is not None:
            if current_pair is None:
                current_pair = ["PASS",_out]
            elif current_pair[0] is None:
                raise Exception("Shouldn't happen")
            elif current_pair[1] is None:
                current_pair[1] = _out
            else:
                current_pair[1] = current_pair[1] + " " + _out
    if current_pair:
        if current_pair[0] is None:
            raise Exception("shouldn't happen")
        if current_pair[1] is None:
            current_pair[1] = "PASS"
        output_pairs.append(current_pair)
    return output_pairs
                

def seq2seq_instance(session, agent_index):
    a = session.scenario["agents"][agent_index]
    rs = a["sorted_restaurants"]
    sf = a["spending_func"]
    cf = a["cuisine_func"]
    input_pairs= [[s,None] for s in gen_seq2seq_input(sf,cf,rs)]
    conversation_pairs = list(gen_seq2seq_conversation(session.events, agent_index))
    all_pairs = input_pairs + conversation_pairs
    all_pairs = coalesce_pairs(all_pairs)
    return all_pairs

def _agents_agree(session):
    def _last_selection(session,uid):
        selection_events = list(e for e in session.events if e["type"]==EventTypes.Selection and e["user"]==uid)
        if selection_events:
            return max(enumerate(selection_events),key=lambda x: x[0])[1]
        else:
            return None
    s0 = _last_selection(session,0)
    s1 = _last_selection(session,1)
    if s0 is None or s1 is None:
        return False
    else:
        return s0["selection"] == s1["selection"]
        

def _conversation_long_enough(session):
    return len(session.events) >= 9

def _nonzero_utility_for_both_users(session):
    # TODO
    return True

def session_filter(s):
    return _agents_agree(s) and _conversation_long_enough(s) and _nonzero_utility_for_both_users(s)

def gen_seq2seq_instances(session):
    for i in range(len(session.scenario["agents"])):
        if session_filter(session):
            instance = seq2seq_instance(session, i)
            if instance:
                yield instance
            

def write_simple_seq2seq_training(sessions, fname):
    with open(fname,"w") as fout:
        for s in sessions:
            for instance in gen_seq2seq_instances(s):
                inputs = [i[0] for i in instance]
                outputs = [i[1] for i in instance]
                input_str = " | ".join(inputs)
                output_str = " | ".join(outputs)
                fout.write("{}\t{}\n".format(input_str,output_str))
    
        


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-transcript_prefix", type=str, nargs="+", help="file prefix(es) for transcripts")
    parser.add_argument("-chat_db_file", type=str, nargs="+", help="Chat database file(s)")
    parser.add_argument("-scenarios_files", type=str, nargs="+", help="Scenarios json files")
    parser.add_argument("-output_prefix", type=str, required=True, help="Output file prefix")
    args = parser.parse_args()

    tfiles = list(itertools.chain(*(glob.glob("{}*".format(p)) for p in args.transcript_prefix)))

    assert len(tfiles)>0

    if DEBUG:
        tfiles = tfiles[:10]

    # output files
    sessions_file = "{}.all_events".format(args.output_prefix)
    scenarios_file = "{}.all_scenarios".format(args.output_prefix)
    s2s_file = "{}.s2s".format(args.output_prefix)

    # parse input files
    scenarios = {v["uuid"]:v for v in itertools.chain(*(load_json_from_file(f) for f in args.scenarios_files))}
    sessions = [ChatSession(fn,scenarios) for fn in tfiles]

    # write output files
    write_chat_sessions_file(sessions, sessions_file)
    write_merged_scenarios_file(scenarios, scenarios_file)
    write_simple_seq2seq_training(sessions, s2s_file)
    
