import os
import sys
import numpy as np
import argparse
import csv
import subprocess
from image import ImageMaker



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-csv", type=str, required=True, help="input CSV file with drawing task results")
    parser.add_argument("-image_field", type=str, default="Input.image_url", help="Name of CSV field containing image url")
    parser.add_argument("-description_field", type=str, default="Answer.TranscriptionTexts", help="Name of CSV field containing mturk worker descriptions")
    parser.add_argument("-worker_id_field", type=str, default="WorkerId", help="Name of CSV field containing mturk worker ID")
    parser.add_argument("-work_time_field", type=str, default="WorkTimeInSeconds", help="Name of CSV field containing mturk work time")
    parser.add_argument("-output_file", type=str, default=None, help="File to write to")
    parser.add_argument("-upload", action="store_true", default=False, help="Publish to HTML server")
    parser.add_argument("-upload_loc", type=str, default="jacob.stanford.edu:/u/apache/htdocs/mkayser/reports/", help="Location to publish HTML doc to")
    parser.add_argument("-url_loc", type=str, default="http://nlp.stanford.edu/mkayser/reports/", help="URL location where report will appear")
    args = parser.parse_args()
            
    if not args.output_file:
        args.output_file = "{}.html".format(os.path.basename(args.csv))

    workers = {}
    worker_counts = {}

    html_lines = []

    work_times = []
    total_work_time = 0
    nrows = 0

    with open(args.csv) as fin:
        reader = csv.reader(fin)
        header = next(reader)
        image_index = header.index(args.image_field)
        descr_index = header.index(args.description_field)
        worker_id_index = header.index(args.worker_id_field)
        work_time_index = header.index(args.work_time_field)

        for i,row in enumerate(reader):
            image_url = row[image_index]
            description = row[descr_index]
            worker_id = row[worker_id_index]
            work_time = float(row[work_time_index])
            
            worker_index = workers.setdefault(worker_id, len(workers))
            worker_counts.setdefault(worker_index,0)
            worker_counts[worker_index] += 1

            nrows += 1

            work_times.append(work_time)
            total_work_time += work_time
                
            lines = [s.strip() for s in description.replace("\r","").split("\n")]
            html_lines.append("<h2>{}</h2>".format(image_url))
            html_lines.append("<h2>Worker: #{:02d}</h2>".format(worker_index))
            html_lines.append("<img src=\"{}\">".format(image_url))
            html_lines.append("<br>")
            html_lines.append(" <br> ".join(lines) + " <br> <br>")
            html_lines.append("<hr>")

    average_work_time = float(total_work_time) / float(nrows)
    work_times = sorted(work_times)

    with open(args.output_file, "w") as fout:
        fout.write("<HTML>")
        for index in np.arange(10) * .1 * nrows:
            index = int(index)
            print("Time ({:.0f} percentile) {}s <br>".format(100*(float(index)/float(nrows)),work_times[index]))
        for i in range(len(workers)):
            count = worker_counts[i]
            fout.write("Worker {:02d} ({} hits) <br> \n".format(i,count)) 
        for line in html_lines:
            fout.write(line)
        fout.write("</HTML>")

    if args.upload:
        upload_command = "scp {} {}".format(args.output_file, args.upload_loc)
        assert subprocess.call(upload_command, shell=True)==0, "Command failed: {}".format(upload_command)
        print("Upload visible at {}/{}".format(args.url_loc, args.output_file))
    
