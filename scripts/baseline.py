__author__ = 'anushabala'

import argparse
import random
import evaluate
import events
import numpy as np
import bitmap


def load_data(train_file, test_file):
    train_infile = open(train_file, 'Ur')
    test_infile = open(test_file, 'Ur')

    train_data = [line.strip().split("\t") for line in train_infile.readlines()]
    test_data = [line.strip().split("\t") for line in test_infile.readlines()]

    return train_data, test_data


def pick_random(dataset):
    return dataset[random.randint(0, len(dataset)-1)]


def run_baseline(test_data, train_data, baseline_type="random_train", verbose=False):
    total_hamming_distance = 0.0
    source_dataset = train_data if baseline_type == "random_test" else test_data
    ctr = 0
    for example in test_data:

        selected = pick_random(source_dataset)

        true_sequence_absolute = events.AbsoluteEventSequence.from_string(example[1])
        pred_sequence_absolute = events.AbsoluteEventSequence.from_string(selected[1])

        bmpmaker.clear()
        bmpmaker.process_commands(true_sequence_absolute.events)
        true_bitmap = np.array(bmpmaker.bitmap)

        bmpmaker.clear()
        bmpmaker.process_commands(pred_sequence_absolute.events)
        pred_bitmap = np.array(bmpmaker.bitmap)

        hamming = evaluate.evaluate(true_bitmap, pred_bitmap)
        total_hamming_distance += hamming

        ctr +=1
        if verbose and ctr % 500 == 0:
            print "Progress: %d" % ctr

    avg_hamming = total_hamming_distance/len(test_data)
    print "Average Hamming distance: %2.2f" % avg_hamming


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-bitmap_dim", type=int, default=15, help="Width of bitmap in blocks (assumed square)")
    parser.add_argument("-train_file", type=str, required=True, help="Path to file containing training data with "
                                                                     "absolute event sequence")
    parser.add_argument("-test_file", type=str, required=True, help="Path to file containing test data with "
                                                                    "absolute event sequence")
    parser.add_argument("-baseline_type", type=str, default="random_train", help="Type of baseline to run - either one"
                                                                                 + " of random_train or random_test")
    parser.add_argument("-v", type=bool, default=False, help="Print progress of baseline evaluation")
    args = parser.parse_args()

    bitmap_dim = args.bitmap_dim

    bmpmaker = bitmap.BitmapMaker(args.bitmap_dim, args.bitmap_dim)
    if args.baseline_type != "random_train" and args.baseline_type != "random_test":
        raise ValueError("Baseline type should be either random_train or random_test")
    train, test = load_data(args.train_file, args.test_file)
    random.seed(0)

    run_baseline(test, train, args.baseline_type, verbose=args.v)

