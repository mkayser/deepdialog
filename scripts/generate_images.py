import os
import sys
import numpy as np
from PIL import Image

output_dir = "output"
npics = 1000
ndots = 10
dim = 6
stayprob = .8
keepdirprob = .8
width = 16
padding = 2

class ImageMaker(object):
    w=width
    s=padding
    grayscalecolors = np.array([255,32,128],dtype=np.dtype(np.uint8))
    
    def __init__(self):
        pass

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


def genpic(ndots, dim, stayprob, keepdirprob):
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
                        antecedentprob = (1-stayprob)/len(dots[:-1])
                        probs = np.append(probs, antecedentprob * .125)
                        events.append((dot,newdot))

        lastdot = dots[-1]
        for x in [lastdot[0]-1,lastdot[0],lastdot[0]+1]:
            for y in [lastdot[1]-1,lastdot[1],lastdot[1]+1]:
                newdot = (x,y)
                if x in range(X) and y in range(Y) and bitmap[newdot]==0:
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


np.random.seed(0)
imgmaker = ImageMaker()


if not os.path.exists(output_dir):
    os.makedirs(output_dir)

for i in range(npics):
    bitmap = genpic(ndots, dim, stayprob, keepdirprob)
    imgmaker.save_bitmap(bitmap, "{}/img_{:04d}.gif".format(output_dir,i))
    np.savetxt("{}/img_{:04d}.txt".format(output_dir,i), bitmap, fmt='%d')
    

