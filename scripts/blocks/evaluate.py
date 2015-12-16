__author__ = 'anushabala'
'''
Provides functions to evaluate the Hamming distance of a Turker-drawn image given a "true" image.
Running this script by itself (with the CSV obtained from the Turk drawing task) produces a histogram of the
Hamming distances of the images produced by the Turkers. Run python evaluate.py -h for details.
'''
import os
import argparse
import re
import csv
from bitmap import *
import matplotlib.pyplot as plt

distance_field = "hamming_distance"
bmp_file_pattern = r'(img_[0-9]+)\.txt'
gif_pattern = r'(img_[0-9]+)\.gif'
global search_area
max_blocks_for_drawn_image = 10
max_hamming = 20

def load_true_images(dirname):
    true_images = {}

    for name in os.listdir(dirname):
        found = re.search(bmp_file_pattern, name)
        if found:
            bmp = np.loadtxt(dirname+'/'+name, dtype=int)
            key = found.group(1)
            true_images[key] = bmp

    return true_images


def evaluate(truth, pred):
    (xdiff, ydiff) = find_corner(truth)
    hamming_distances = []
    search_space = [(xdiff, ydiff)]
    search_space.extend([(x_offset, ydiff) for x_offset in range(xdiff - 5, xdiff + 5) if x_offset != xdiff])
    search_space.extend([(xdiff, y_offset) for y_offset in range(ydiff - 5, ydiff + 5) if y_offset != ydiff])
    search_space.extend([(x_offset, y_offset) for x_offset in range(xdiff - 5, xdiff + 5) for y_offset in range(ydiff - 5, ydiff + 5) if x_offset != xdiff and y_offset != ydiff])

    for (x_offset, y_offset) in search_space:
        aligned_pred, removed_blocks = align(pred, (x_offset, y_offset))
        distance = hamming_distance(truth, aligned_pred)
        distance += removed_blocks
        hamming_distances.append(distance)
        # if there's an exact match, stop
        if distance == 0:
            break

    return min(hamming_distances)

def hamming_distance(truth, pred):
    dist = 0
    (rows, cols) = truth.shape
    for i in range(0, rows):
        for j in range(0, cols):
            if truth[i, j] != pred[i,j]:
                dist += 1

    return dist


def align(pred, corner):
    pred_corner = find_corner(pred)
    (xdiff, ydiff) = tuple([a - b for a, b in zip(pred_corner, corner)])
    aligned, removed_blocks = translate(pred, xdiff, ydiff)
    return aligned, removed_blocks


def translate(bmp, xdiff=0, ydiff=0):
    if xdiff == 0 and ydiff == 0:
        return bmp, 0
    removed_blocks = 0
    aligned_bmp = np.zeros(bmp.shape, dtype=int)
    (rows, cols) = bmp.shape
    for i in range(0, rows):
        for j in range(0, cols):
            if bmp[i,j] == 1:
                if (i - xdiff) in range(0, rows) and (j - ydiff) in range(0, cols):
                    aligned_bmp[i - xdiff, j - ydiff] = 1
                else:
                    # if a block moves off the grid during translation, add 1 to the hamming distance
                    removed_blocks += 1

    return aligned_bmp, removed_blocks


def find_corner(bmp):
    x = -1
    y = -1
    rows, cols = bmp.shape
    for i in range(0, rows):
        if 1 in bmp[i, :]:
            x = i
            break
    for i in range(0, cols):
        if 1 in bmp[:,i]:
            y = i
            break

    return (x,y)

def count_blocks(bmp):
    ctr = 0
    (rows, cols) = bmp.shape
    for i in range(0, rows):
        for j in range(0, cols):
            if bmp[i, j] == 1:
                ctr +=1
    return ctr

def get_hamming_distances(inp, true_image_dir, output_file, generator, image_url_field, actions_field):
    true_images = load_true_images(true_image_dir)
    reader = csv.reader(open(inp, 'Ur'))
    writer = csv.writer(open(output_file, 'w'))
    print output_file
    header = next(reader)
    out_header = list(header)
    out_header.append(distance_field)
    writer.writerow(out_header)

    image_url_index = header.index(image_url_field)
    actions_index = header.index(actions_field)

    ctr = 0
    data_with_distances = []
    too_many_blocks = 0
    too_few_blocks = 0
    exact_matches = 0
    for row in reader:
        ctr += 1
        if ctr % 500 == 0:
            print "Progress: %d" % ctr

        generator.clear()
        commands = row[actions_index]
        image_url = row[image_url_index]
        image_key = re.search(gif_pattern, image_url).group(1)
        generator.process_commands_str(commands)
        drawn_image = generator.bitmap
        num_blocks_drawn = count_blocks(drawn_image)

        if num_blocks_drawn > max_blocks_for_drawn_image:
            print "Skipping row: Too many blocks in drawn image", row
            too_many_blocks += 1
            continue
        elif num_blocks_drawn < max_blocks_for_drawn_image:
            print "Skipping row: Too few blocks in drawn image", row
            too_few_blocks += 1
            continue
        true_image = true_images[image_key]
        distance = evaluate(true_image, drawn_image)
        if distance > max_hamming:
            print "Skipping row: Hamming distance too large (> %d)" % max_hamming, row
            continue
        if distance == 0:
            exact_matches += 1
        row.append(distance)

        writer.writerow(row)

        data_with_distances.append(row)

    print "---------------"

    print "Number of exact matches: %d" % exact_matches
    print "Number of examples with too many blocks: %d" % too_many_blocks
    print "Number of examples with too few blocks: %d" % too_few_blocks

    return data_with_distances, out_header

def get_distance_stats(distances):
    inexact_matches = [x[-1] for x in distances if x[-1] != 0]
    plt.hist(inexact_matches)
    plt.xlabel("Hamming distance")
    plt.ylabel("# of examples")
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-csv", type=str, required=True, help="Input CSV file with results from drawing task")
    parser.add_argument("-image_dir", type=str, required=True, help="Path to directory containing GIFs and txt bitmaps of source images")
    parser.add_argument("-output_file", type=str, required=True, help="Path to output file to write results to. Results file contains each row of the input file (with invalid examples filtered out) with the hamming distance added to the end of the file.")
    parser.add_argument("-bitmap_dim", type=int, default=15, help="Width of bitmap in blocks (assumed square)")
    parser.add_argument("-image_field", type=str, default="Input.Image_url", help="Name of CSV field containing image URL")
    parser.add_argument("-draw_events_field", type=str, default="Answer.WritingTexts", help="Name of CSV field containing drawing task events")
    parser.add_argument("-search_area", type=int, default=5, help="Maximum x and y directions to move drawn image in after superimposing to find minimum hamming distance")

    args = parser.parse_args()
    generator = BitmapMaker(args.bitmap_dim, args.bitmap_dim)
    image_url_field = args.image_field
    actions_field = args.draw_events_field
    search_area = args.search_area
    distances = get_hamming_distances(args.csv, args.image_dir, args.output_file, generator, image_url_field, actions_field)
    get_distance_stats(distances)
