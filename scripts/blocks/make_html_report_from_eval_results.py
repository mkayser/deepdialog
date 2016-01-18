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
import base64
import tempfile


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

def convert_commands_to_bitmap(bmpmaker, commands_str, mode):
    bmpmaker.clear()
    if mode == "relative":
        rel_seq = RelativeEventSequence.from_eval_str(commands_str)
        abs_seq = AbsoluteEventSequence.from_relative(rel_seq, bmpmaker.shape()[0], bmpmaker.shape()[1])
    elif mode == "cursor":
        cur_seq = CursorEventSequence.from_eval_str(commands_str)
        abs_seq = AbsoluteEventSequence.from_cursor(cur_seq, bmpmaker.shape()[0], bmpmaker.shape()[1])
        
    bmpmaker.process_commands(abs_seq.events)
    return (bmpmaker.bitmap.copy(), bmpmaker.ordered_actions)

def save_bitmap_to_file(imgmaker, bitmap, ordered_actions, fn):
    imgmaker.save_bitmap(bitmap, fn, ordered_actions)
    np.savetxt("{}.txt".format(fn), bitmap.flatten(), fmt="%d", newline=" ", footer="\n")

def base64_encode_bitmap(imgmaker, bitmap, ordered_actions):
    with tempfile.TemporaryFile() as f:
        imgmaker.save_bitmap(bitmap, f, ordered_actions, image_format="PNG")
        f.seek(0)
        return base64.b64encode(f.read())

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    
    # Input location and mode
    parser.add_argument("-json", type=str, required=True, help="input json file with eval results")
    parser.add_argument("-mode", type=str, required=True, help="Mode of output sequences, must be 'relative' or 'cursor'")

    # Options pertaining to drawing the pictures
    parser.add_argument("-block_px", type=int, default=16, help="Block width in pixels")
    parser.add_argument("-padding_px", type=int, default=1, help="Padding in pixels")
    parser.add_argument("-bitmap_dim", type=int, default=25, help="Width of bitmap in blocks (assumed square)")
    parser.add_argument("-inline_images", action="store_true", default=False, help="Include images inline")

    # Output location
    parser.add_argument("-output_dir", type=str, required=True, help="Directory to write output to")

    # Options pertaining to uploading to a webserver
    parser.add_argument("-upload", action="store_true", default=False, help="Publish to HTML server")
    parser.add_argument("-upload_loc", type=str, default="mkayser@jacob.stanford.edu:/u/apache/htdocs/mkayser/reports/", help="Location to publish HTML doc to")
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
            
            predpair = convert_commands_to_bitmap(bmpmaker, sample.y_pred, args.mode)
            refpair = convert_commands_to_bitmap(bmpmaker, sample.y_ref, args.mode)


            if args.inline_images:
                pred_img_tag = "<img src=\"data:image/png;base64,{}\" />".format(base64_encode_bitmap(imgmaker, *predpair))
                ref_img_tag = "<img src=\"data:image/png;base64,{}\" />".format(base64_encode_bitmap(imgmaker, *refpair))
            else:
                pred_img_tag = "<img src=\"{}\">".format(y_pred_fn)
                ref_img_tag = "<img src=\"{}\">".format(y_ref_fn)
                save_bitmap_to_file(imgmaker, predpair[0], predpair[1], y_pred_path)
                save_bitmap_to_file(imgmaker, refpair[0], refpair[1], y_ref_path)

            total_hamming += float(sample.hamming_distance)

            html_lines.append("<h2>Sample #{:04d} </h2>".format(i))
            
            html_lines.append("<table><tr> <td width=\"40%%\">{}</td> <td>{}<br>Mturk reference</td> <td width=\"60%%\">{}<br>EncDec output</td> </tr> </table>".format("<br>".join(sample.x), ref_img_tag, pred_img_tag))
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
    
