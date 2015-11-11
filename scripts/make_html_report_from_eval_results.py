import os
import sys
import numpy as np
import argparse
import subprocess
import json
from image import ImageMaker
from bitmap import BitmapMaker
from events import RelativeEventSequence,AbsoluteEventSequence
import urllib

def save_txt_to_file(txt,file_name):
    with open(file_name, "w") as fout:
        fout.write(txt)

def make_dir_unless_exists(dirname):
    try:
        os.mkdir(args.output_dir)
    except OSError:
        pass

class AsNamespace(object):
  def __init__(self, dict_):
    self.__dict__.update(dict_)

def convert_rel_commands_to_image_and_save_to_file(bmpmaker, imgmaker, rel_commands_str, fn):
    bmpmaker.clear()
    rel_seq = RelativeEventSequence.from_eval_str(rel_commands_str)
    abs_seq = AbsoluteEventSequence.from_relative(rel_seq, bmpmaker.shape()[0], bmpmaker.shape()[1])
    bmpmaker.process_commands(abs_seq.events)
    imgmaker.save_bitmap(bmpmaker.bitmap, fn, bmpmaker.ordered_actions)
    np.savetxt("{}.txt".format(fn), bmpmaker.bitmap.flatten(), fmt="%d", newline=" ", footer="\n")

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    
    # Input location
    parser.add_argument("-json", type=str, required=True, help="input json file with eval results")

    # Options pertaining to drawing the pictures
    parser.add_argument("-block_px", type=int, default=16, help="Block width in pixels")
    parser.add_argument("-padding_px", type=int, default=1, help="Padding in pixels")
    parser.add_argument("-bitmap_dim", type=int, default=25, help="Width of bitmap in blocks (assumed square)")

    # Output location
    parser.add_argument("-output_dir", type=str, required=True, help="Directory to write output to")

    # Options pertaining to uploading to a webserver
    parser.add_argument("-upload", action="store_true", default=False, help="Publish to HTML server")
    parser.add_argument("-upload_loc", type=str, default="anusha@jacob.stanford.edu:/u/apache/htdocs/mkayser/reports/", help="Location to publish HTML doc to")
    parser.add_argument("-url_loc", type=str, default="http://nlp.stanford.edu/mkayser/reports/", help="URL location where report will appear")
    args = parser.parse_args()

    output_file = "report.html"

    imgmaker = ImageMaker(args.block_px, args.padding_px)
    bmpmaker = BitmapMaker(args.bitmap_dim, args.bitmap_dim)

    make_dir_unless_exists(args.output_dir)

    with open(args.json) as fin:
        eval_info = json.load(fin)
        html_lines = []
        total_hamming = 0.0
        for i,sample in enumerate(eval_info):
            sample = AsNamespace(sample)

            gen_filenames = lambda x: [prefix + "{}.{:04d}.gif".format(x,i) for prefix in ("","{}/".format(args.output_dir))]

            y_pred_fn, y_pred_path = gen_filenames("y_pred")
            y_ref_fn, y_ref_path = gen_filenames("y_ref")
            
            convert_rel_commands_to_image_and_save_to_file(bmpmaker, imgmaker, sample.y_pred, y_pred_path)
            convert_rel_commands_to_image_and_save_to_file(bmpmaker, imgmaker, sample.y_ref, y_ref_path)

            total_hamming += float(sample.hamming_distance)

            html_lines.append("<h2>Sample #{:04d} </h2>".format(i))
            
            html_lines.append("<table><tr> <td width=\"40%%\">{}</td> <td><img src=\"{}\"><br>Mturk reference</td> <td width=\"60%%\"><img src=\"{}\"><br>EncDec output</td> </tr> </table>".format("<br>".join(sample.x), y_ref_fn, y_pred_fn))
            html_lines.append("<br>")
            html_lines.append("<hr>")

    avg_distance = total_hamming/len(eval_info)

    with open("{}/{}".format(args.output_dir,output_file), "w") as fout:
        fout.write("<HTML>")

        fout.write("<h2> Results </h2> <br>")
        fout.write("<h3> Average Hamming distance: %2.2f </h3> <br>" % avg_distance)
        for line in html_lines:
            fout.write(line)
        fout.write("</HTML>")

    if args.upload:
        upload_command = "scp -r {} {}".format(args.output_dir, args.upload_loc)
        assert subprocess.call(upload_command, shell=True)==0, "Command failed: {}".format(upload_command)
        print("Upload visible at {}/{}/{}".format(args.url_loc, args.output_dir, output_file))
    
