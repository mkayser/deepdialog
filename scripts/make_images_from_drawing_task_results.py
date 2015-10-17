import os
import sys
import numpy as np
import argparse
import csv
from image import ImageMaker
from bitmap import BitmapMaker



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-width", type=int, default=32, help="Width of blocks in pixels")
    parser.add_argument("-padding", type=int, default=2, help="Padding of blocks in pixels")
    parser.add_argument("-dim", type=int, default=5, help="Dimensionality of grid")
    parser.add_argument("-csv", type=str, required=True, help="input CSV file with drawing task results")
    parser.add_argument("-field", type=str, default="Answer.WritingTexts", help="Name of CSV field containing draw events")
    parser.add_argument("-output_dir", type=str, default="output/make_images_from_drawing_task_results", help="output directory for images")
    args = parser.parse_args()

    imgmaker = ImageMaker(args.width, args.padding)
    bmpmaker = BitmapMaker(args.width, args.width)
    np.random.seed(0)

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)


    with open(args.csv) as fin:
        reader = csv.reader(fin)
        header = next(reader)
        colindex = header.index(args.field)
        for i,row in enumerate(reader):
            commands_str = row[colindex]
            bmpmaker.clear()
            bmpmaker.process_commands_str(commands_str)
            bitmap = bmpmaker.bitmap
            bitmap_file = "{}/img_{:04d}.gif".format(args.output_dir,i)
            imgmaker.save_bitmap(bitmap, bitmap_file)
    

