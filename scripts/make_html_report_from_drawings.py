import os
import sys
import numpy as np
import argparse
import csv
import subprocess
import itertools
import re
from image import ImageMaker
from bitmap import BitmapMaker
import urllib

def save_txt_to_file(txt,file_name):
    with open(file_name, "w") as fout:
        fout.write(txt)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-csv", type=str, required=True, help="input CSV file with drawing task results")
    parser.add_argument("-block_px", type=int, default=32, help="Block width in pixels")
    parser.add_argument("-padding_px", type=int, default=2, help="Padding in pixels")
    parser.add_argument("-bitmap_dim", type=int, required=True, help="Width of bitmap in blocks (assumed square)")
    parser.add_argument("-image_field", type=str, default="Input.Image_url", help="Name of CSV field containing image url")
    parser.add_argument("-commands_field", type=str, default="Input.commands", help="Name of CSV field containing commands")
    parser.add_argument("-draw_events_field", type=str, default="Answer.WritingTexts", help="Name of CSV field containing saved drawing events")
    parser.add_argument("-worker_id_field", type=str, default="WorkerId", help="Name of CSV field containing mturk worker ID")
    parser.add_argument("-work_time_field", type=str, default="WorkTimeInSeconds", help="Name of CSV field containing mturk work time")
    parser.add_argument("-output_dir", type=str, required=True, help="Directory to write output to")
    parser.add_argument("-upload", action="store_true", default=False, help="Publish to HTML server")
    parser.add_argument("-upload_loc", type=str, default="jacob.stanford.edu:/u/apache/htdocs/mkayser/reports/", help="Location to publish HTML doc to")
    parser.add_argument("-url_loc", type=str, default="http://nlp.stanford.edu/mkayser/reports/", help="URL location where report will appear")
    args = parser.parse_args()

    output_file = "report.html"

    workers = {}
    worker_counts = {}

    html_lines = []

    work_times = []
    total_work_time = 0
    nrows = 0

    imgmaker = ImageMaker(args.block_px, args.padding_px)
    bmpmaker = BitmapMaker(args.bitmap_dim, args.bitmap_dim)

    try:
        os.mkdir(args.output_dir)
    except OSError:
        pass

    with open(args.csv) as fin:
        reader = csv.reader(fin)
        header = next(reader)

        image_index = header.index(args.image_field)
        commands_index = header.index(args.commands_field)
        draw_events_index = header.index(args.draw_events_field)
        worker_id_index = header.index(args.worker_id_field)
        work_time_index = header.index(args.work_time_field)

        #rows = sorted(list(reader),lambda a,b:cmp(a[image_index],b[image_index]))
        rows = list(reader)

        for i,row in enumerate(rows):
            true_image_url = row[image_index]
            commands = row[commands_index]
            draw_events = row[draw_events_index]
            worker_id = row[worker_id_index]
            work_time = float(row[work_time_index])
            
            worker_index = workers.setdefault(worker_id, len(workers))
            worker_counts.setdefault(worker_index,0)
            worker_counts[worker_index] += 1

            nrows += 1

            work_times.append(work_time)
            total_work_time += work_time

            # Save true bitmap GIF and TXT to directory
            true_txt_url = true_image_url.replace(".gif",".txt")

            true_image_file = "true_img_{:04d}.gif".format(i)
            true_txt_file = "true_img_{:04d}.txt".format(i)
            urllib.urlretrieve (true_image_url, "{}/{}".format(args.output_dir,true_image_file))
            urllib.urlretrieve (true_txt_url, "{}/{}".format(args.output_dir,true_txt_file))

            # Make GIF from draw events
            bmpmaker.clear()
            bmpmaker.process_commands_str(draw_events)
            bitmap = bmpmaker.bitmap
            drawn_image_file = "drawn_img_{:04d}.gif".format(i)
            drawn_image_save_path = "{}/{}".format(args.output_dir,drawn_image_file)
            imgmaker.save_bitmap(bitmap, drawn_image_save_path)

            # Make TXT from draw events
            drawn_txt_file = "drawn_img_{:04d}.txt".format(i)
            drawn_txt_save_path = "{}/{}".format(args.output_dir,drawn_txt_file)
            np.savetxt(drawn_txt_save_path, bitmap, fmt='%d')

            # Save command text and generated events text too
            commands_txt_file = "written_commands_{:04d}.txt".format(i)
            events_txt_file = "draw_events_{:04d}.txt".format(i)
            save_txt_to_file(commands.replace("<br>","\n"), "{}/{}".format(args.output_dir,commands_txt_file))
            save_txt_to_file(draw_events, "{}/{}".format(args.output_dir,events_txt_file))

            
            html_lines.append("<h2>Worker: #{:03d} ({}) (WORKER_{:03d}_NUM_HITS hits) </h2>".format(worker_index,worker_id,worker_index))
            html_lines.append("<b>Image: {}</b> <br>".format(true_image_url))
            
            html_lines.append("<table><tr> <td><img src=\"{}\"><br>Original</td> <td>{}</td> <td><img src=\"{}\"><br>Drawn</td> </tr> </table>".format(true_image_url,commands,drawn_image_file))
            html_lines.append("<br>")
            html_lines.append("<hr>")

    average_work_time = float(total_work_time) / float(nrows)
    work_times = sorted(work_times)

    for i in range(len(workers)):
        html_lines = [l.replace("WORKER_{:03d}_NUM_HITS".format(i), str(worker_counts[i])) for l in html_lines]

    with open("{}/{}".format(args.output_dir,output_file), "w") as fout:
        fout.write("<HTML>")

        fout.write("<h2> {} total HIT's </h2>".format(nrows))
        fout.write("<h2> Time stats </h2> <br>")
        for index in np.arange(10) * .1 * nrows:
            index = int(index)
            fout.write("Time ({:.0f} percentile) {}s <br>".format(100*(float(index)/float(nrows)),work_times[index]))

        fout.write("<h2> Worker output </h2> <br>")
        for i in range(len(workers)):
            count = worker_counts[i]
            fout.write("{} Worker {:03d} ({} hits) <br> {} \n".format("<b>" if count>50 else "",i,count,"</b>" if count>50 else "")) 

        fout.write("<h2> Results </h2> <br>")
        for line in html_lines:
            fout.write(line)
        fout.write("</HTML>")

    if args.upload:
        upload_command = "scp -r {} {}".format(args.output_dir, args.upload_loc)
        assert subprocess.call(upload_command, shell=True)==0, "Command failed: {}".format(upload_command)
        print("Upload visible at {}/{}/{}".format(args.url_loc, args.output_dir, output_file))
    
