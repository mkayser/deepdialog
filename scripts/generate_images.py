import sys
import numpy as np
from PIL import Image

npics = 100
ndots = 10
dim = 6
stayprob = .8
keepdirprob = .8
width = 16
padding = 2

class ImageMaker(object):
    w=width
    s=padding
    colors = ["39f0","ffff","888f"]
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

    def save_bitmap_as_bmp(self, bitmap, outfile):
        img_array = self.make_image_array(bitmap)
        grayscale = self.grayscalecolors[img_array.astype(np.uint8)]
        image = Image.fromarray(grayscale)
        image.save(outfile)

    def save_bitmap_as_png(self, bitmap, outfile):
        img_array = self.make_image_array(bitmap)
        buf = "".join([self.colors[i] for i in list(img_array.flatten())])
        data = self.write_png(buf, img_array.shape[0], img_array.shape[1])
        with open(outfile, 'wb') as fd:
            fd.write(data)

    # I got this function from stackoverflow: http://stackoverflow.com/questions/902761/saving-a-numpy-array-as-an-image
    def write_png(self, buf, width, height):
        """ buf: must be bytes or a bytearray in py3, a regular string in py2. formatted RGBARGBA... """
        import zlib, struct

        # reverse the vertical line order and add null bytes at the start
        width_byte_4 = width * 4
        raw_data = b''.join(b'\x00' + buf[span:span + width_byte_4]
                            for span in range((height - 1) * width * 4, -1, - width_byte_4))

        def png_pack(png_tag, data):
            chunk_head = png_tag + data
            return (struct.pack("!I", len(data)) +
                    chunk_head +
                    struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head)))

        return b''.join([
            b'\x89PNG\r\n\x1a\n',
            png_pack(b'IHDR', struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0)),
            png_pack(b'IDAT', zlib.compress(raw_data, 9)),
            png_pack(b'IEND', b'')])
        

def displaystr(bit):
    return "O" if bit else "."

def printpic(bitmap):
    for r in range(bitmap.shape[0]):
        for c in range(bitmap.shape[1]):
            print(displaystr(bitmap[r][c])),
        print("")
    print("")


def genpic2(ndots, dim, stayprob, keepdirprob):
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

for i in range(npics):
    bitmap = genpic2(ndots, dim, stayprob,keepdirprob)
    #printpic(bitmap)
    imgmaker.save_bitmap_as_bmp(bitmap, "img_{:02d}.bmp".format(i))

