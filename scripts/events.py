__author__ = 'mkayser'
'''
Provides basic classes to represent absolute or relative event sequences.
'''



def is_int(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False


class AbsoluteEventSequence(object):
    events = []

    def __init__(self, events):
        self.events = events

    def __str__(self):
        return " ".join([" ".join(map(str,l)) for l in self.events])

    # Strip out any block adds which are later deleted
    def canonicalize(self):
        keep = [True for e in self.events]
        for i,e in enumerate(self.events):
            if e[0] == "DEL":
                for j in range(i+1):
                    if self.events[j][1:] == e[1:]:
                        keep[j]=False
        canonical_events = [list(e) for e,k in zip(self.events,keep) if k]
        return AbsoluteEventSequence(canonical_events)

    @classmethod
    def from_mturk_string(cls, events_str):
        lines = events_str.strip().replace("\r","").split("\n")
        events = []
        for l in lines:
            action,arg1,arg2 = l.strip().split()
            events.append([action, int(arg1), int(arg2)])
        return cls(events)

    @classmethod
    def from_relative(cls,rel,gridx,gridy):
        abs_events = []
        prevpos = None

        for i,e in enumerate(rel.events):
            if e == ["START"]:
                assert(prevpos is None)
                pos = [int(gridx/2),int(gridy/2)]
            elif e[0] == "PUT":
                assert(prevpos is not None)
                pos = [prevpos[0]+e[1], prevpos[1]+e[2]]
            else:
                raise Exception("Unsupported relative event: {}".format(e))
            abs_events.append(["PUT", pos[0], pos[1]])
            prevpos = pos
        return cls(abs_events)


class RelativeEventSequence(object):
    events = []

    def __init__(self, events):
        self.events = events

    def __str__(self):
        return " ".join([" ".join(map(str,l)) for l in self.events])

    @classmethod
    def from_absolute(cls, absolute):
        events = absolute.events
        rel_events = []
        prevpos = [None,None]

        for i,e in enumerate(events):
            pos = e[1:]
            if i==0: 
                rel_events.append(["START"])
            else:
                jump = [a-b for a,b in zip(pos,prevpos)]
                rel_events.append(["PUT"] + jump)
            prevpos = pos

        return cls(rel_events)

    @classmethod
    def from_tokens(cls, tokens):
        i=0
        events = []
        while i<len(tokens):
            if tokens[i] == "START":
                if i==0:
                    events.append(["START"])
                else:
                    pass
                i += 1
            elif tokens[i] == "PUT":
                if i==0:
                    i += 1
                else:
                    if i+2 < len(tokens) and is_int(tokens[i+1]) and is_int(tokens[i+2])):
                        events.append(["PUT",int(tokens[i+1]),int(tokens[i+2])])
                        i += 3
                    else:
                        i += 1
        return cls(events)


