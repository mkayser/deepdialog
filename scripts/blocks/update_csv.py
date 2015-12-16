import os
import sys
import numpy as np
import argparse
import csv
import subprocess
import itertools
import collections
import re
from image import ImageMaker

ACCEPTACTION="accept"
REJECTACTION="reject"
NOACTION    ="no action taken"

ACCEPTSTATUS="accepted"
REJECTSTATUS="rejected"
NOSTATUS="blank"

def accept(row,accept_index,reject_index):
    output_row = list(row)
    while(max(accept_index,reject_index) >= len(output_row)):
        output_row.append("")
    output_row[accept_index] = "X"
    output_row[reject_index] = ""
    return (ACCEPTACTION,ACCEPTSTATUS,output_row)

def reject(row,accept_index,reject_index,rejection_message):
    output_row = list(row)
    while(max(accept_index,reject_index) >= len(output_row)):
        output_row.append("")
    output_row[accept_index] = ""
    output_row[reject_index] = rejection_message
    assert(rejection_message is not None)
    return REJECTACTION,REJECTSTATUS,output_row
    

def accept_or_reject_using_key(row,accept_index,reject_index,key_index,good_keys,bad_keys,rejection_message):
    output_row = list(row)

    if row[key_index] in good_keys:
        while(max(accept_index,reject_index) >= len(output_row)):
            output_row.append("")
        output_row[accept_index] = "X"
        output_row[reject_index] = ""
        return (ACCEPTACTION,ACCEPTSTATUS,output_row)
        
    elif row[key_index] in bad_keys:
        while(max(accept_index,reject_index) >= len(output_row)):
            output_row.append("")
        output_row[accept_index] = ""
        output_row[reject_index] = rejection_message
        assert(rejection_message is not None)
        return REJECTACTION,REJECTSTATUS,output_row
    else:
        if accept_index<len(output_row) and output_row[accept_index].strip() != "":
            status = ACCEPTSTATUS
        elif reject_index<len(output_row) and output_row[reject_index].strip() != "":
            status = REJECTSTATUS
        else:
            status = NOSTATUS
        return NOACTION,status,output_row

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-csv", type=str, required=True, help="input CSV file with drawing task results")
    parser.add_argument("-worker_id_field", type=str, default="WorkerId", help="Name of CSV field containing mturk worker ID")
    parser.add_argument("-accept_field", type=str, default="Approve", help="Name of CSV field containing approval")
    parser.add_argument("-reject_field", type=str, default="Reject", help="Name of CSV field containing rejection")

    parser.add_argument('-accept_workers',default=[],action='store',type=str, nargs='*')
    parser.add_argument('-reject_workers',default=[],action='store',type=str, nargs='*')

    parser.add_argument("-accept_all", type=bool, default=False, help="Accept all HIT's")    
    parser.add_argument("-reject_all", type=bool, default=False, help="Reject all HIT's")    

    parser.add_argument("-rejection_message", default=None, type=str, help="Message to rejected workers")
    
    parser.add_argument("-output_csv", type=str, default=None, help="File to write to")
    args = parser.parse_args()
            
    if not args.output_csv:
        args.output_csv = args.csv

    accept_workers = set(args.accept_workers)
    reject_workers = set(args.reject_workers)

    with open(args.csv) as fin:
        reader = csv.reader(fin)
        header = next(reader)
        worker_id_index = header.index(args.worker_id_field)
        accept_index = header.index(args.accept_field)
        reject_index = header.index(args.reject_field)
        rows = list(reader)

    if args.accept_all:
        triples = [accept(r,accept_index,reject_index) for r in rows]
    elif args.reject_all:
        triples = [reject(r,accept_index,reject_index,args.rejection_message) for r in rows]
    else:
        triples = [accept_or_reject_using_key(r,
                                              accept_index,
                                              reject_index,
                                              worker_id_index,
                                              accept_workers,
                                              reject_workers,
                                              args.rejection_message) for r in rows]
    
    actions = collections.Counter(t[0] for t in triples)
    statuses = collections.Counter(t[1] for t in triples)
    rows = [t[2] for t in triples]

    print("Actions taken:")
    print(dict(actions).items())
    print("Current status:")
    print(dict(statuses).items())

    with open(args.output_csv,"w") as fout:
        writer = csv.writer(fout)
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)
    
