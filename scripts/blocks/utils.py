__author__ = 'anushabala'
import csv

def read_csv(inp):
    reader = csv.reader(open(inp, 'Ur'))
    header = next(reader) # skip header
    data = [row for row in reader]
    return header, data
