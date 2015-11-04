import numpy as np

class BitmapMaker(object):
    bitmap = None
    
    def __init__(self, xdim, ydim):
        int_t = np.dtype(np.int32)
        self.bitmap = np.zeros((xdim,ydim), dtype=int_t)

    def shape(self):
        return self.bitmap.shape

    def clear(self):
        self.bitmap[...] = 0

    def process_command(self, c):
        val = 0
        if c[0]=="ADD":
            val = 1
        else:
            assert c[0]=="DEL", "command is neither ADD nor DEL: {}".format(c)
        self.bitmap[int(c[1])][int(c[2])] = val

    def process_commands(self, commands):
        for c in commands:
            self.process_command(c)

    def process_commands_str(self, commands_str):
        commands = [s.strip().split() for s in commands_str.replace("\r","").split("\n")]
        self.process_commands(commands)

