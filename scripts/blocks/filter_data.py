__author__ = 'anushabala'
'''
Provides functions to filter Turker-drawn images based on their Hamming distance from the original (generated) image.
Run python filter_data.py -h for details.
'''
import argparse
import csv
import evaluate
from bitmap import *
import utils


def filter(data, header, cutoff, output_file):
    print "Filtering data...."
    total = 0
    filtered = 0
    kept = 0
    writer = csv.writer(open(output_file, 'w'))
    writer.writerow(header)
    for row in data:
        total += 1
        dist = row[-1]
        if dist <= cutoff:
            kept += 1
            writer.writerow(row)
        else:
            filtered += 1

    print "Total examples: %d\nKept %d examples\nRemoved %d examples with cutoff > %d" % (total, kept, filtered, cutoff)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-csv", type=str, required=True, help="Input CSV file with Hamming distances for each example [or raw data from Turk drawing task; see the -compute_distance parameter")
    parser.add_argument("-output", type=str, required=True, help="Path to output file containing filtered data")
    parser.add_argument("-compute_distances", type=bool, help="If true, the Hamming distance for each example will be calculated first")
    parser.add_argument("-cutoff", type=int, default=8, help="Specifies a cutoff Hamming distance (defaults to 8). Any examples with a Hamming distance greater than this value will be filtered out.")
    parser.add_argument("-image_dir", type=str, help="(Required if compute_distances is true) Path to directory containing GIFs and txt bitmaps of source images")
    parser.add_argument("-bitmap_dim", type=int, default=15, help="(Only used if compute_distances = True) Width of bitmap in blocks (assumed square)")
    parser.add_argument("-image_field", type=str, default="Input.Image_url", help="(Only used if compute_distances = True) Name of CSV field containing image URL")
    parser.add_argument("-draw_events_field", type=str, default="Answer.WritingTexts", help="(Only used if compute_distances = True) Name of CSV field containing drawing task events")

    args = parser.parse_args()
    input_file = args.csv
    data_with_distance = []
    file_header = []
    if args.compute_distances:
        if not args.image_dir:
            parser.print_help()
            raise ValueError("-image_dir parameter is required if -compute_distances is true.")
        generator = BitmapMaker(args.bitmap_dim, args.bitmap_dim)
        image_url_field = args.image_field
        actions_field = args.draw_events_field
        data_with_distance, file_header = evaluate.get_hamming_distances(args.csv, args.image_dir, args.output, generator, image_url_field, actions_field)
    else:
        data_with_distance, file_header = utils.read_csv(input_file)

    filter(data_with_distance, file_header, args.cutoff, args.output)