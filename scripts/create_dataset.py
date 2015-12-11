__author__ = 'anushabala, mkayser'
'''
Provides functions to create training, test, and validation datasets given a file containing raw data from the drawing
task. Run python create_datasets.py -h for details.
'''
import argparse
import os
import re
import random
from treebank_tokenizer import TreebankWordTokenizer
from events import AbsoluteEventSequence, RelativeEventSequence, CursorEventSequence
from bitmap import BitmapMaker
from utils import read_csv
from align import align_strings
import urllib2
from io import StringIO
from collections import defaultdict
import numpy as np
import json

gif_pattern = r'(img_[0-9]+)\.gif'

def image_url_to_key(url):
    image_key = re.search(gif_pattern, url).group(1)
    return image_key

def image_url_to_text_bitmap_url(url):
    return url.replace(".gif",".txt")

def retrieve_bitmap(url):
    response = urllib2.urlopen(url)
    #txtio = StringIO(response.read())
    return np.loadtxt(response)

def bitmap_to_list(b):
    if b is not None:
        bl = b.tolist()
        return ["".join([str(i) for i in l]) for l in bl]
    else:
        return None

def tokenize_description(tokenizer, text):
    def add_punct(line):
        if line.strip()[-1] not in ".!\"\',?":
            return line + " . "
        else:
            return line

    lines = text.split("</br>")
    tok_lines = [" ".join(tokenizer.tokenize(l)).lower() for l in lines]
    punct_tok_lines = [add_punct(l) for l in tok_lines if l.strip()]
    return " ".join(punct_tok_lines)


# Return three lists of image keys
def split_keys(rows, image_idx, train_ratio, test_ratio, val_ratio):
    image_keys = set()

    for row in rows:
        image_keys.add(image_url_to_key(row[image_idx]))

    image_keys = sorted(list(image_keys))
    random.shuffle(image_keys)

    l = float(len(image_keys))

    train_end = int(l * train_ratio)
    test_end = int(train_end + l * test_ratio)
    val_end = len(image_keys)

    train = image_keys[0:train_end]
    test = image_keys[train_end:test_end]
    val = image_keys[test_end:val_end]

    attrs = defaultdict(dict)
    for items,name in zip([train,test,val],["train","test","val"]):
        for key in items:
            attrs[key]["data_split"] = name

    print "attrs = {}".format(attrs)

    return attrs

def write_data(rows, key_attrs, image_idx, commands_idx, actions_idx, output_file, include_bitmaps=True, grid_dims=(25,25)):
    tokenizer = TreebankWordTokenizer()
    bmpmaker = BitmapMaker(grid_dims[0],grid_dims[1])

    with open(output_file, "w") as fout:
        objs = []
        for i,row in enumerate(rows):

            if i % 100 == 0:
                print "  {}  ".format(i)

            image_url = row[image_idx]
            if include_bitmaps:
                bitmap = retrieve_bitmap(image_url_to_text_bitmap_url(image_url))
            else:
                bitmap = None
            
            image_key = image_url_to_key(image_url)
            commands = tokenize_description(tokenizer, row[commands_idx])
            actions = row[actions_idx]

            abs_seq = AbsoluteEventSequence.from_mturk_string(actions).canonicalize()
            rel_seq = RelativeEventSequence.from_absolute(abs_seq)
            cur_seq = CursorEventSequence.from_absolute(abs_seq)

            abs_str = str(abs_seq)
            rel_str = str(rel_seq)
            cur_str = str(cur_seq)

            raw_txt = actions.replace("\r", "").replace("\n"," ")

            rel_alignments,well_aligned = align_strings(commands, rel_str, "relative", "clever", grid_dims[0], backup_using_naive=True)
            
            str_rel_alignments = []
            for c,r in rel_alignments:
                r_str = " ".join(str(i) for l in r for i in l)
                str_rel_alignments.append((c,r_str))

            obj = {}
            obj["image_url"] = image_url
            obj["image_id"] = image_key
            obj["commands"] = commands  
            obj["actions.absolute"] = abs_str
            obj["actions.relative"] = rel_str
            obj["actions.cursor"] = cur_str
            obj["alignments.relative"] = str_rel_alignments
            obj["alignments_type.relative"] = "clever_heuristic" if well_aligned else "naive_heuristic"

            for key,val in key_attrs[image_key].iteritems():
                obj[key] = val

            if bitmap is not None:                
                abs_norm_seq = AbsoluteEventSequence.from_relative(rel_seq, grid_dims[0], grid_dims[1])

                try:
                    bmpmaker.clear()
                    bmpmaker.process_commands(abs_norm_seq.events)
                    bitmap_mturk_norm = bmpmaker.bitmap.copy()
                except:
                    bitmap_mturk_norm = None
                    

                try:
                    bmpmaker.clear()
                    bmpmaker.process_commands(abs_seq.events)                
                    bitmap_mturk = bmpmaker.bitmap.copy()
                except:
                    bitmap_mturk = None
                
                obj["actions.absolute.normalized"] = str(abs_norm_seq)
                obj["bitmap.orig_generated"] = bitmap_to_list(bitmap.astype(np.int_))
                obj["bitmap.from_mturk"] = bitmap_to_list(bitmap_mturk.astype(np.int_))
                obj["bitmap.normalized"] = bitmap_to_list(bitmap_mturk_norm)
            objs.append(obj)
        json.dump(objs, fout, indent=4, sort_keys=True)

        print "Created dataset at %s" % output_file


if __name__=="__main__":
    valid_modes = ["relative","cursor","raw","absolute"]

    parser = argparse.ArgumentParser()
    parser.add_argument("-csv", type=str, required=True, help="Input CSV file with Hamming distances for each example [or raw data from Turk drawing task; see the -compute_distance parameter")
    parser.add_argument("-output_json_file", type=str, required=True, help="Output json file")
    
    parser.add_argument("-rseed", type=int, default=0, help="Random seed")
    parser.add_argument("-train_ratio", type=float, default=0.67, help="Ratio (between 0 and 1) of examples to use for training")
    parser.add_argument("-test_ratio", type=float, default=0.17, help="Ratio (between 0 and 1) of examples to use for testing")
    parser.add_argument("-val_ratio", type=float, default=0.16, help="Ratio (between 0 and 1) of examples to use for validation")
    parser.add_argument("-commands_field", type=str, default="Input.commands", help="Name of CSV field containing descriptions to arrange blocks")
    parser.add_argument("-image_field", type=str, default="Input.Image_url", help="Name of CSV field containing image URL")
    parser.add_argument("-retrieve_text_bitmaps", type=bool, default=True, help="Retrieve and augment data with bitmaps located adjacent to image URL's")
    parser.add_argument("-draw_events_field", type=str, default="Answer.WritingTexts", help="Name of CSV field containing drawing task events")

    args = parser.parse_args()

    random.seed(args.rseed)

    header, rows = read_csv(args.csv)

    commands_idx = header.index(args.commands_field)
    actions_idx = header.index(args.draw_events_field)
    image_idx = header.index(args.image_field)

    key_attrs = split_keys(rows, image_idx, args.train_ratio, args.test_ratio, args.val_ratio)
    output_file = args.output_json_file

    d = os.path.dirname(output_file)
    if not os.path.exists(d) and len(d)>0:
        os.makedirs(d)

    print "Processing {} rows".format(len(rows))
    write_data(rows, key_attrs, image_idx, commands_idx, actions_idx, output_file, include_bitmaps=args.retrieve_text_bitmaps)
