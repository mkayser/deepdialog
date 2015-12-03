__author__ = 'anushabala'
from argparse import ArgumentParser
import json
from bitmap import BitmapMaker
from evaluate import evaluate
from events import AbsoluteEventSequence, RelativeEventSequence, CursorEventSequence
import numpy as np

def update_json(inp_data, mode):
    updated_data = []
    ctr = 0
    for example in inp_data:
        bmpmaker.clear()
        if mode == "relative":
            true_seq_relative = RelativeEventSequence.from_eval_str(example["y_ref"])
            true_events_absolute = AbsoluteEventSequence.from_relative(true_seq_relative, width, width).events
            pred_seq_relative = RelativeEventSequence.from_eval_str(example["y_pred"])
            pred_events_absolute = AbsoluteEventSequence.from_relative(pred_seq_relative, width, width).events
        elif mode == "cursor":
            true_seq_cursor = CursorEventSequence.from_eval_str(example["y_ref"])
            true_events_absolute = AbsoluteEventSequence.from_cursor(true_seq_cursor, width, width).events
            pred_seq_cursor = CursorEventSequence.from_eval_str(example["y_pred"])
            pred_events_absolute = AbsoluteEventSequence.from_cursor(pred_seq_cursor, width, width).events
        else:
            raise Exception("Unknown or unsupported mode: {}".format(mode))
            

        bmpmaker.process_commands(true_events_absolute)
        true_bitmap = np.array(bmpmaker.bitmap)

        bmpmaker.clear()
        bmpmaker.process_commands(pred_events_absolute)
        pred_bitmap = np.array(bmpmaker.bitmap)
        hamming = evaluate(true_bitmap, pred_bitmap)
        example["hamming_distance"] = hamming
        updated_data.append(example)
        ctr+=1

        if ctr % 500 == 0:
            print "Progress: %d" % ctr

    return updated_data



if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-json", type=str, required=True, help="Input JSON to add Hammings distances to.")
    parser.add_argument("-mode", type=str, required=True, help="Format of output sequences: [relative,cursor]")
    
    parser.add_argument("-output", type=str, default="", help="Output file to write updated JSON to. If not specified, a suffix "
                                                  "is added to the input file to create the output file.")
    parser.add_argument("-width", type=int, default=25, help="Width of bitmap (assume square) - use larger number than size"
                                                            " of original bitmap to allow for conversion of relative sequences"
                                                             " to absolute sequences")
    args = parser.parse_args()
    input_file = args.json
    mode = args.mode
    output_file = args.output if args.output else "%s-with-hamming.json" % (input_file[:input_file.rfind("/")]
                                                                            + input_file[input_file.rfind("/"):].replace(".json", ""))
    width = args.width
    input_data = json.load(open(input_file, 'Ur'))
    bmpmaker = BitmapMaker(width, width)

    output_data = update_json(input_data, mode)
    json.dump(output_data, open(output_file, 'w'), sort_keys=True, indent=4)
