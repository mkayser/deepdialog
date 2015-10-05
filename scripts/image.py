import numpy as np
from PIL import Image

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
