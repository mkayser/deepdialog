__author__ = 'anushabala'
import os
import sys
import shutil
dirname = sys.argv[1]
outdir = sys.argv[2]

if os.path.exists(outdir):
    print "Output directory already exists! Deleting everything in it..."
    shutil.rmtree(outdir)

os.makedirs(outdir)
ctr = 0
for name in os.listdir(dirname):
    f = open(os.path.join(dirname, name))
    outfile = open(os.path.join(outdir, name), 'w')

    for line in f.readlines():
        cols = line.strip().split("\t")
        if len(cols) > 2 and "has user ID" in cols[2]:
            first_line = cols[0:1]
            try:
                date_idx = cols[2].index("02-24-2016")
                user_id_col = cols[2][:date_idx]
                first_line.append(user_id_col)
                second_line = [cols[2][date_idx:]]
                second_line.extend(cols[3:])
                outfile.write("\t".join(first_line)+"\n")
                outfile.write("\t".join(second_line)+"\n")
            except ValueError:
                print f.name
                print line
                print "------"
                outfile.close()
                os.remove(outfile.name)
        else:
            outfile.write(line)

    outfile.close()
    f.close()

    ctr += 1

    if ctr % 100 == 0:
        print "Cleared up %d transcripts" % ctr