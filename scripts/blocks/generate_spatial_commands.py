import sys
import os
import random
import re

command_template = "Place $BLOCKNUM $RELATION the last block"

relations = "above,below,to the left of,to the right of,on top of,on the bottom of".split(",")
blocknums = "a block,a block,a block,a block,two blocks".split(",")

def create_command(template, slotvals):
    tokens = template.split()
    output_tokens = []
    for t in tokens:
        if t.startswith("$"):
            output_tokens.append(slotvals.pop(0))
        else:
            output_tokens.append(t)
    return " ".join(output_tokens)

def blocknum_conflict(prev,curr):
    return False

def relation_type(relation_str):
    if re.search(r'above|top', relation_str):
        return "UP"
    if re.search(r'below|bottom', relation_str):
        return "DOWN"
    if re.search(r'left', relation_str):
        return "LEFT"
    if re.search(r'right', relation_str):
        return "RIGHT"
    assert False, "Shouldn't get here"


def relation_conflict(prev,curr):
    prev_type = relation_type(prev)
    curr_type = relation_type(curr)
    types = (prev_type,curr_type)
    #print("TYPES: {}".format(types))
    if types==("UP","DOWN") or types==("DOWN","UP") or types==("LEFT","RIGHT") or types==("RIGHT","LEFT"):
        #print("CONFLICT: {} .... {}".format(prev,curr))
        return True
    return False

def conflict(prev_values, values):
    if not prev_values:
        #print("SKIPPING")
        return False
    return blocknum_conflict(prev_values[0],values[0]) or relation_conflict(prev_values[1],values[1])

def generate_commands(n):
    yield "Place a block in the middle of the grid"
    prev_values = None
    for i in range(1,n):
        values = None
        #print("VALUES={}    PREV={}".format(values,prev_values))
        while (not values) or conflict(prev_values,values):
            values = [random.choice(blocknums), random.choice(relations)]
        #print("OKVALUES={}".format(values))
        prev_values = values[:]
        yield create_command(command_template, values)
        #print("PREV={}".format(prev_values))

def generate_csv_for_mturk(num_hits,n):
    print("COMMANDS")
    for i in range(num_hits):
        commands = list(generate_commands(n))
        print(" <br> ".join(commands))
            
generate_csv_for_mturk(1000,10)        
