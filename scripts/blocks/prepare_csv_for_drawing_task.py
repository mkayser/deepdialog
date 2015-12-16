__author__ = 'anushabala'
import csv
import argparse

replace_labels = {"Answer.TranscriptionTexts":"commands",
                    "Input.image_url":"Image_url"}
data_label = "commands"

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-inp", type=str, required=True, help="Path to CSV file with data from block description HITs")
    parser.add_argument("-out", type=str, required=True, help="Path to desired output file")
    args = parser.parse_args()
    input_file = args.inp
    output_file = args.out

    reader = csv.reader(open(input_file, 'Ur'))
    writer = csv.writer(open(output_file, 'w'))
    header = next(reader)
    for (orig_label, new_label) in replace_labels.iteritems():
        i = header.index(orig_label)
        header[i] = new_label

    index = header.index(data_label)

    writer.writerow(header)

    for row in reader:
        text = row[index]
        print text
        print "------------"
        new_text = text.replace("\n", "</br>")
        print new_text
        refmt_row = list(row)
        refmt_row[index] = new_text
        writer.writerow(refmt_row)


