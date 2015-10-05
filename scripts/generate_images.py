import os
import sys
import numpy as np
import argparse
from image import ImageMaker


def displaystr(bit):
    return "O" if bit else "."

def printpic(bitmap):
    for r in range(bitmap.shape[0]):
        for c in range(bitmap.shape[1]):
            print(displaystr(bitmap[r][c])),
        print("")
    print("")


def generate_bitmap_and_commands(ndots, dim, stayprob, keepdirprob, diag, randstart):
    int_t = np.dtype(np.int32)
    bitmap = np.zeros((dim,dim),dtype=int_t)
    dots = []

    if randstart:
        firstdot = tuple(np.random.randint(dim,size=(2,)))    
    else:
        firstdot = ((dim+1)/2,(dim+1)/2)

    commands = ["START"]
    actions = ["ADD {} {}".format(firstdot[0],firstdot[1])]
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
        if np.sum(probs) < .001:
            break
        probs = probs / np.sum(probs)
        prevdot,newdot = events[np.random.choice(len(events),p=probs)]
        momentum = (newdot[0]-prevdot[0], newdot[1]-prevdot[1])
        bitmap[newdot] = 1
        dots.append(newdot)

        if prevdot != lastdot:
            actions.append("JUMP {} {}".format(prevdot[0], prevdot[1]))
            commands.append("JUMP {} {}".format(prevdot[0], prevdot[1]))

        actions.append("ADD {} {}".format(newdot[0],newdot[1]))
        if momentum == (-1,-1):
            commands.append("UPLEFT")
        elif momentum == (-1,0):
            commands.append("UP")
        elif momentum == (-1,1):
            commands.append("UPRIGHT")
        elif momentum == (0,-1):
            commands.append("LEFT")
        elif momentum == (0,1):
            commands.append("RIGHT")
        elif momentum == (1,-1):
            commands.append("DOWNLEFT")
        elif momentum == (1,0):
            commands.append("DOWN")
        elif momentum == (1,1):
            commands.append("DOWNRIGHT")
        else:
            assert False, "Bad momentum: {}".format(momentum)

    return bitmap,commands,actions


def write_text_to_file(text, file_name):
    with open(file_name,"w") as fout:
        fout.write(text + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-width", type=int, default=32, help="Width of blocks in pixels")
    parser.add_argument("-padding", type=int, default=2, help="Padding of blocks in pixels")
    parser.add_argument("-npics", type=int, default=1000, help="Num pictures to produce")
    parser.add_argument("-nblocks", type=int, default=10, help="Num blocks to place")
    parser.add_argument("-dim", type=int, default=5, help="Dimensionality of grid")
    parser.add_argument("-rprob", type=float, default=.8, help="Recency probability")
    parser.add_argument("-mprob", type=float, default=.8, help="Momentum probability")
    parser.add_argument("-diag", action="store_true", default=False, help="Allow diagonals")
    parser.add_argument("-uniq", action="store_true", default=False, help="Enforce uniqueness")
    parser.add_argument("-debug", action="store_true", default=False, help="Print output to console, don't create files")
    parser.add_argument("-randstart", action="store_true", default=False, help="Start drawing at random position")
    parser.add_argument("-output_dir", type=str, default="output/generate_images", help="output directory for images")
    args = parser.parse_args()

    imgmaker = ImageMaker(args.width, args.padding)
    np.random.seed(0)

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    bitmaps = set()

    for i in range(args.npics):

        bitmap=None
        while bitmap is None or (args.uniq and tuple(bitmap.flatten()) in bitmaps):
            bitmap,commands,actions = generate_bitmap_and_commands(args.nblocks, args.dim, args.rprob, args.mprob, args.diag, args.randstart)
        bitmaps.add(tuple(bitmap.flatten()))
        
        if args.debug:
            np.savetxt(sys.stdout, bitmap, fmt='%d')
            print("")
        else:
            bitmap_file = "{}/img_{:04d}.gif".format(args.output_dir,i)
            numpy_file = "{}/img_{:04d}.txt".format(args.output_dir,i)
            numpy_flat_file = "{}/img_flat_{:04d}.txt".format(args.output_dir,i)
            proto_commands_file = "{}/proto_commands_{:04d}.txt".format(args.output_dir,i)
            actions_file = "{}/actions_{:04d}.txt".format(args.output_dir,i)
            imgmaker.save_bitmap(bitmap, bitmap_file)
            np.savetxt(numpy_file, bitmap, fmt='%d')
            np.savetxt(numpy_flat_file, bitmap.flatten()[None,:], fmt='%d')
            write_text_to_file(" _ ".join(commands), proto_commands_file)
            write_text_to_file(" _ ".join(actions), actions_file)
    

