# from https://stackoverflow.com/questions/4373741/how-can-i-randomly-place-several-non-colliding-rects

import random
from random import randint
random.seed()


class LocalPoint(object): # to distinguish it from shapely points and what not...
    def __init__(self, x, y):
        self.x, self.y = x, y

    @staticmethod
    def from_point(other):
        return LocalPoint(other.x, other.y)

class Rect(object):
    def __init__(self, x1, y1, x2, y2):
        minx, maxx = (x1,x2) if x1 < x2 else (x2,x1)
        miny, maxy = (y1,y2) if y1 < y2 else (y2,y1)
        self.min, self.max = LocalPoint(minx, miny), LocalPoint(maxx, maxy)

    @staticmethod
    def from_points(p1, p2):
        return Rect(p1.x, p1.y, p2.x, p2.y)

    width  = property(lambda self: self.max.x - self.min.x)
    height = property(lambda self: self.max.y - self.min.y)


def quadsect(rect, factor):
    """ Subdivide given rectangle into four non-overlapping rectangles.
        'factor' is an integer representing the proportion of the width or
        height the deviatation from the center of the rectangle allowed.
    """

    plus_or_minus = lambda v: v * [-1, 1][(randint(0, 100) % 2)]  # equal chance +/-1

    # pick a point in the interior of given rectangle
    w, h = rect.width, rect.height  # cache properties
    center = LocalPoint(rect.min.x + (w // 2), rect.min.y + (h // 2))
    delta_x = plus_or_minus(randint(0, w // factor))
    delta_y = plus_or_minus(randint(0, h // factor))
    interior = LocalPoint(center.x + delta_x, center.y + delta_y)

    # create rectangles from the interior point and the corners of the outer one
    return [Rect(interior.x, interior.y, rect.min.x, rect.min.y),
            Rect(interior.x, interior.y, rect.max.x, rect.min.y),
            Rect(interior.x, interior.y, rect.max.x, rect.max.y),
            Rect(interior.x, interior.y, rect.min.x, rect.max.y)]

def square_subregion(rect):
    """ Return a square rectangle centered within the given rectangle """
    w, h = rect.width, rect.height  # cache properties
    if w < h:
        offset = (h - w) // 2
        return Rect(rect.min.x, rect.min.y+offset,
                    rect.max.x, rect.min.y+offset+w)
    else:
        offset = (w - h) // 2
        return Rect(rect.min.x+offset, rect.min.y,
                    rect.min.x+offset+h, rect.max.y)


def return_random_rectangles(num_rectangles, num_recs_to_generate = 20, region = Rect(0, 0, 640, 480)):

    # call quadsect() until at least the number of rects wanted has been generated
    rects = [region]   # seed output list
    while len(rects) <= num_recs_to_generate:
        rects = [subrect for rect in rects
                            for subrect in quadsect(rect, 3)]

    random.shuffle(rects)  # mix them up
    sample = random.sample(rects, num_rectangles)  # select the desired number

    return sample