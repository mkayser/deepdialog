import numpy as np
from PIL import Image, ImageDraw, ImageFont


class ImageMaker(object):
    w=None
    s=None
    grayscalecolors=None
    default_font = ImageFont.truetype("Arial.ttf", size=12)
    
    def __init__(self, width, padding, colors=[255,32,128]):
        self.w = width
        self.s = padding
        self.grayscalecolors = np.array(colors,dtype=np.dtype(np.uint8))

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

    def save_bitmap(self, bitmap, outfile, ordered_actions=None, image_format="GIF"):
        img_array = self.make_image_array(bitmap)
        grayscale = self.grayscalecolors[img_array.astype(np.uint8)]
        image = Image.fromarray(grayscale)
        image = image.convert("RGB")
        if ordered_actions:
            drawn_positions = {}
            draw = ImageDraw.Draw(image)
            for (idx,position) in enumerate(ordered_actions):
                row = position[0]
                col = position[1]
                top_left_xdim = col * (self.w + 2*self.s) + self.s + self.w/2
                top_left_ydim = row * (self.w + 2*self.s) + self.s + 1

                if (top_left_xdim, top_left_ydim) in drawn_positions.keys():
                    drawn_positions[(top_left_xdim, top_left_ydim)].append(str(idx))
                else:
                    drawn_positions[(top_left_xdim, top_left_ydim)] = [str(idx)]

            for ((top_left_xdim, top_left_ydim), indexes) in drawn_positions.iteritems():
                draw.text((top_left_xdim, top_left_ydim), ",".join(indexes), fill=(255, 255, 255), font=self.default_font)
        image.save(outfile, image_format)
