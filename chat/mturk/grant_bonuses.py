__author__ = 'anushabala'
from boto.mturk.connection import MTurkConnection
from boto.mturk.price import Price
from argparse import ArgumentParser
import csv
import sqlite3

access_key = 'AKIAJR4ULNPXFICAGAXA'
secret_key = '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'


def grant_bonuses(mturk_conn, db_cursor, results_csv):
    reader = csv.reader(results_csv)
    header = reader.next()
    assignment_idx = header.index('AssignmentId')
    worker_idx = header.index('WorkerId')
    code_idx = header.index('Answer.surveycode')

    for row in reader:
        assignmentid = row[assignment_idx]
        workerid = row[worker_idx]
        code = row[code_idx]

        cursor.execute('SELECT bonus FROM CompletedTasks WHERE mturk_code=?', (code,))
        result = cursor.fetchone()
        if not result:
            print "ERROR: Couldn't find submitted MTurk code %s in database." % code
        else:
            if result[0] == 1:
                print "Granting bonus to worker %s with MTurk code %s" % (workerid, code)
                mturk_connection.grant_bonus(workerid, assignmentid, Price(amount=0.50),
                                             reason='For great negotiation skills!')

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-m', type=str, default='SANDBOX', help="Mode ('SANDBOX' or 'PROD')")
    parser.add_argument('-f', type=str, required=True, help="Path to CSV results from MTurk")
    parser.add_argument('--db', type=str, default='../chat_state.db', help='Path to database containing survey codes. Defaults to ../chat_state.db')

    args = parser.parse_args()
    mode = args.m
    db = args.db
    results_file = args.f

    host = 'mechanicalturk.sandbox.amazonaws.com'
    if mode == 'PROD':
        host = 'mechanicalturk.amazonaws.com'

    mturk_connection = MTurkConnection(aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key,
                                 host=host)

    mturk_connection.grant_bonus('A29YQT3EEC0ZEC', '3RRCEFRB7N6QG0IIYO46PS2CSS64B9', Price(amount=0.50),
                           reason='just testing this')

    db_connection = sqlite3.connect(db)
    with db_connection:
        cursor = db_connection.cursor()
        grant_bonuses(mturk_connection, cursor, results_file)

    db_connection.close()
