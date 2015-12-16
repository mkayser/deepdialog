import json
import sys
import argparse
import os

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-json", type=str, required=True, help="Input json file")
    parser.add_argument("-alignments_field", type=str, default="alignments.relative", help="Alignments field in json objects")
    parser.add_argument("-output_prefix", type=str, required=True, help="Output file prefix")

    args = parser.parse_args()

    with open(args.json) as fin:
        j = json.load(fin)

    d = os.path.dirname(args.output_prefix)
    if not os.path.exists(d) and len(d)>0:
        os.makedirs(d)

    files = {}

    for o in j:
        pairs = o[args.alignments_field]
        left = " | ".join(p[0] for p in pairs)
        right = " | ".join(p[1] for p in pairs)
        split = o["data_split"]
        if split not in files:
            files[split] = open("{}.{}".format(args.output_prefix, split), "w")
        fout = files[split]
        fout.write("{}\t{}\n".format(left,right))

    for key,fout in files.items():
        fout.close()
