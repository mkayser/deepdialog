import os
import sys
import numpy as np
import argparse
import subprocess
import json
from image import ImageMaker
from bitmap import BitmapMaker
from events import RelativeEventSequence,AbsoluteEventSequence,CursorEventSequence
import urllib

def make_dir_unless_exists(dirname):
    try:
        os.mkdir(args.output_dir)
    except OSError:
        pass

def convert_commands_to_image_sequence(bmpmaker, imgmaker, commands_str, fprefix, mode):
    bmpmaker.clear()
    if mode == "relative":
        rel_seq = RelativeEventSequence.from_eval_str(commands_str)
        abs_seq = AbsoluteEventSequence.from_relative(rel_seq, bmpmaker.shape()[0], bmpmaker.shape()[1])
    elif mode == "cursor":
        cur_seq = CursorEventSequence.from_eval_str(commands_str)
        abs_seq = AbsoluteEventSequence.from_cursor(cur_seq, bmpmaker.shape()[0], bmpmaker.shape()[1])
        
    imgmaker.save_bitmap(bmpmaker.bitmap, "{}{:04d}.gif".format(fprefix,0))
    for i,c in enumerate(abs_seq.events):
        bmpmaker.process_command(c)
        imgmaker.save_bitmap(bmpmaker.bitmap, "{}{:04d}.gif".format(fprefix,i+1))

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    
    # Input location and mode
    parser.add_argument("-commands", type=str, required=True, help="command sequence")
    parser.add_argument("-mode", type=str, required=True, help="Mode of sequence, must be 'relative' or 'cursor'")

    # Options pertaining to drawing the pictures
    parser.add_argument("-block_px", type=int, default=16, help="Block width in pixels")
    parser.add_argument("-padding_px", type=int, default=1, help="Padding in pixels")
    parser.add_argument("-bitmap_dim", type=int, default=25, help="Width of bitmap in blocks (assumed square)")

    # Output location
    parser.add_argument("-output_dir", type=str, required=True, help="Directory to write output to")

    args = parser.parse_args()

    output_file = "report.html"

    imgmaker = ImageMaker(args.block_px, args.padding_px)
    bmpmaker = BitmapMaker(args.bitmap_dim, args.bitmap_dim)

    make_dir_unless_exists(args.output_dir)

    convert_commands_to_image_sequence(bmpmaker, imgmaker, args.commands, "{}/img_".format(args.output_dir), args.mode)

    
