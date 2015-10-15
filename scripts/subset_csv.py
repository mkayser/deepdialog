import os
import sys
import argparse
import csv
import re
import rowset
import random
from collections import defaultdict

def read_list_from_file(file_name):
    results = []
    with open(file_name) as fin:
        for line in fin:
            results.append(line.strip())
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-csv", type=str, required=True, help="input CSV file with drawing task results")
    parser.add_argument("-rejected_workers", type=str, default=None, help="plaintext file containing list of rejected worker ID's")
    parser.add_argument("-num_per_image", type=int, required=True, help="max # rows per image")
    parser.add_argument("-output_csv", type=str, required=True, help="output CSV")
    args = parser.parse_args()

    random.seed(0)

    row_set = rowset.RowSet.from_file(args.csv)

    image_instances = defaultdict(list)

    image_field = "Input.image_url"
    worker_id_field = "WorkerId"

    image_idx = row_set.index_of(image_field)
    worker_id_idx = row_set.index_of(worker_id_field)

    if args.rejected_workers:
        rejected_workers = read_list_from_file(args.rejected_workers)

    rejected_row_count = 0

    for r in row_set.rows:
        if r[worker_id_idx] not in rejected_workers:
            image = r[image_idx]
            image_instances[image].append(r)
        else:
            rejected_row_count += 1

    output_rows = []
    unused_rows = []
    for image,rows in image_instances.items():
        subset = []
        if len(rows) > args.num_per_image:
            shuffled = list(rows)
            random.shuffle(shuffled)
            subset = shuffled[:args.num_per_image]
            unused = shuffled[args.num_per_image:]
        else:
            subset = list(rows)
            unused = []

        output_rows.extend(subset)
        unused_rows.extend(unused)

    num_requested = args.num_per_image * len(image_instances)
    num_unfulfilled = num_requested - len(output_rows)

    additional_rows = random.sample(unused_rows, min(len(unused_rows), num_unfulfilled))

    output_rows.extend(additional_rows)

    print("{} rows per image requested".format(args.num_per_image))
    print("{} images".format(len(image_instances)))
    print("{} total rows requested".format(num_requested))
    print("{} rows from rejected workers excluded".format(rejected_row_count))
    print("{} unfulfilled (not enough samples for some images)".format(num_unfulfilled))
    print("{} additional rows randomly sampled from unused".format(len(additional_rows)))
    print("= {} total rows in sample".format(len(output_rows)))

    output_row_set = rowset.RowSet(row_set.headers, output_rows)
    output_row_set.save(args.output_csv)
    print("{} total rows written to file {}".format(len(output_rows), args.output_csv))

