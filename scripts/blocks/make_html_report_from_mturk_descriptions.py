import os
import sys
import numpy as np
import argparse
import csv
import subprocess
import itertools
import re
from treebank_tokenizer import TreebankWordTokenizer
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
    wordcounts = {}

    tokenizer = TreebankWordTokenizer()

    with open(args.csv) as fin:
        reader = csv.reader(fin)
        header = next(reader)
        image_index = header.index(args.image_field)
        descr_index = header.index(args.description_field)
        worker_id_index = header.index(args.worker_id_field)
        work_time_index = header.index(args.work_time_field)

        rows = sorted(list(reader),lambda a,b:cmp(a[image_index],b[image_index]))

        for i,row in enumerate(rows):
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
            words = itertools.chain(*[tokenizer.tokenize(l) for l in lines])
            for w in words:
                wordcounts.setdefault(w.lower(),0)
                wordcounts[w.lower()] += 1

            html_lines.append("<h2>{}</h2>".format(image_url))
            html_lines.append("<h2>Worker: #{:03d} ({}) (WORKER_{:03d}_NUM_HITS hits) </h2>".format(worker_index,worker_id,worker_index))
            html_lines.append("<b>Image: {}</b> <br>".format(image_url))
            
            html_lines.append("<img src=\"{}\">".format(image_url))
            html_lines.append("<br>")
            html_lines.append(" <br> ".join(lines) + " <br> <br>")
            html_lines.append("<hr>")

    average_work_time = float(total_work_time) / float(nrows)
    work_times = sorted(work_times)
    freq_words = sorted(wordcounts.iteritems(), lambda a,b: cmp(b[1],a[1]))
    total_word_count = sum([t[1] for t in freq_words])

    for i in range(len(workers)):
        html_lines = [l.replace("WORKER_{:03d}_NUM_HITS".format(i), str(worker_counts[i])) for l in html_lines]

    with open(args.output_file, "w") as fout:
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

        fout.write("<h2> Word stats </h2> <br>")
        running_total=0
        fout.write("<table>")
        for i,pair in enumerate(freq_words):
            w,c = pair
            running_total += c
            pct = 100.0 * float(c) / total_word_count
            cum_pct = 100.0 * float(running_total)/total_word_count
            fout.write("<tr><td>{}</td> <td>{}</td> <td>{}</td> <td>{:.2f}</td> <td>({:.2f})</td></tr> \n".format(i, w, c, pct, cum_pct)) 
        fout.write("</table>")

        fout.write("<h2> Results </h2> <br>")
        for line in html_lines:
            fout.write(line)
        fout.write("</HTML>")

    if args.upload:
        upload_command = "scp {} {}".format(args.output_file, args.upload_loc)
        assert subprocess.call(upload_command, shell=True)==0, "Command failed: {}".format(upload_command)
        print("Upload visible at {}/{}".format(args.url_loc, args.output_file))
    
