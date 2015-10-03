import os
import sys
import numpy as np
from PIL import Image
import argparse

output_dir = "output"
npics = 1000
ndots = 10
dim = 5
stayprob = .8
keepdirprob = .8


class ImageMaker(object):
    w=None
    s=None
    grayscalecolors = np.array([255,32,128],dtype=np.dtype(np.uint8))
    
    def __init__(self, width, padding):
        self.w = width
        self.s = padding

    def make_block(self):
        s = self.s
        w = self.w
        b = np.full((w+2*s, w+2*s), 2, dtype=np.dtype(np.int32))
        b[s:s+w,s:s+w] = 1
        return b

    def make_nonblock(self):
        s = self.s
        w = self.w
        b = np.full((w+2*s, w+2*s), 2, dtype=np.dtype(np.int32))
        b[s:s+w,s:s+w] = 0
        return b

    def make_image_array(self,bitmap):
        squares = [self.make_nonblock(), self.make_block()]
        rows = []
        for i in range(bitmap.shape[0]):
            rows.append(np.hstack([squares[k] for k in list(bitmap[i])]))
        return np.vstack(rows)

    def save_bitmap(self, bitmap, outfile):
        img_array = self.make_image_array(bitmap)
        grayscale = self.grayscalecolors[img_array.astype(np.uint8)]
        image = Image.fromarray(grayscale)
        image.save(outfile)

def displaystr(bit):
    return "O" if bit else "."

def printpic(bitmap):
    for r in range(bitmap.shape[0]):
        for c in range(bitmap.shape[1]):
            print(displaystr(bitmap[r][c])),
        print("")
    print("")


def genpic(ndots, dim, stayprob, keepdirprob, diag):
    int_t = np.dtype(np.int32)
    bitmap = np.zeros((dim,dim),dtype=int_t)
    dots = []
    firstdot = tuple(np.random.randint(dim,size=(2,)))
    bitmap[firstdot] = 1
    dots.append(firstdot)
    momentum = (0,0)

    for k in range(1,ndots):
        # for each antecedent, for each neighbor, accumulate probability to neighbor
        # pick from this probability distribution
        X,Y = bitmap.shape
        events = []
        probs = np.zeros((0,))
        for dot in dots[:-1]:
            for x in [dot[0]-1,dot[0],dot[0]+1]:
                for y in [dot[1]-1,dot[1],dot[1]+1]:
                    newdot = (x,y)
                    if x in range(X) and y in range(Y) and bitmap[newdot]==0:
                        if not diag and x != dot[0] and y != dot[1]:
                            continue
                            
                        antecedentprob = (1-stayprob)/len(dots[:-1])
                        probs = np.append(probs, antecedentprob * .125)
                        events.append((dot,newdot))

        lastdot = dots[-1]
        for x in [lastdot[0]-1,lastdot[0],lastdot[0]+1]:
            for y in [lastdot[1]-1,lastdot[1],lastdot[1]+1]:
                newdot = (x,y)
                if x in range(X) and y in range(Y) and bitmap[newdot]==0:
                    if not diag and x != lastdot[0] and y != lastdot[1]:
                        continue
                    antecedentprob = stayprob
                    if momentum == (0,0):
                        newprob = antecedentprob * .125
                    elif momentum == (x-lastdot[0], y-lastdot[1]):
                        newprob = antecedentprob * keepdirprob
                    else:
                        newprob = antecedentprob * (1-keepdirprob)/7
                    probs = np.append(probs, newprob)
                    events.append((lastdot, newdot))
        probs = probs / np.sum(probs)
        prevdot,newdot = events[np.random.choice(len(events),p=probs)]
        momentum = (newdot[0]-prevdot[0], newdot[1]-prevdot[1])
        bitmap[newdot] = 1
        dots.append(newdot)
    return bitmap



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-width", type=int, default=32, help="Width of blocks in pixels")
    parser.add_argument("-padding", type=int, default=2, help="Padding of blocks in pixels")
    parser.add_argument("-npics", type=int, default=1000, help="Num pictures to produce")
    parser.add_argument("-nblocks", type=int, default=10, help="Num blocks to place")
    parser.add_argument("-dim", type=int, default=5, help="Dimensionality of grid")
    parser.add_argument("-rprob", type=float, default=.8, help="Recency probability")
    parser.add_argument("-mprob", type=float, default=.8, help="Momentum probability")
    parser.add_argument("-diag", type=bool, default=False, help="Allow diagonals")
    parser.add_argument("-debug", type=bool, default=False, help="Print output to console, don't create files")
    parser.add_argument("-output_dir", type=str, default="output/generate_images", help="output directory for images")
    args = parser.parse_args()

    imgmaker = ImageMaker(args.width, args.padding)
    np.random.seed(0)

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    for i in range(args.npics):
        bitmap = genpic(args.nblocks, args.dim, args.rprob, args.mprob, args.diag)
        if args.debug:
            np.savetxt(sys.stdout, bitmap, fmt='%d')
            print("")
        else:
            imgmaker.save_bitmap(bitmap, "{}/img_{:04d}.gif".format(args.output_dir,i))
            np.savetxt("{}/img_{:04d}.txt".format(args.output_dir,i), bitmap, fmt='%d')
    

