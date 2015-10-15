import csv

class RowSet(object):
    headers=None
    rows=None

    def __init__(self, headers, rows):
        self.headers = headers
        self.rows = rows

    def index_of(self, field):
        assert (field in self.headers)
        index = self.headers.index(field)
        return index

    def sort_by(self, field, comparer=None):
        if not comparer:
            comparer=cmp
        index = self.index_of(field)
        self.rows = sorted(self.rows, lambda r,s: comparer(r[index],s[index]))

    def save(self, file_name):
        with open(file_name, "w") as fout:
            writer = csv.writer(fout)
            writer.writerow(self.headers)
            for r in self.rows:
                writer.writerow(r)

    @classmethod
    def from_file(cls, file_name):
        with open(file_name) as fin:
            reader = csv.reader(fin)
            headers = next(reader)
            rows = list(reader)
        return cls(headers,rows)
