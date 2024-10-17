""" Random rectangles generator
    
    From the code provided by martineau at https://stackoverflow.com/questions/4373741/how-can-i-randomly-place-several-non-colliding-rects
    (accessed 16 October 2024)

    This script allows the user to slice up a rectangular region into lots of tiny rectangles, which should non-overlapping, in a fairly computationally efficient way (more efficient than generating rectangles and checking whether it is non-overlapping with all the previously generated rectangles)
    
    This script requires the packages random and shapely.geometry (the latter of which is required anyway for other scripts)


""" 

import random
from shapely.geometry import Point
from random import randint, uniform
random.seed()

class Rect(object):
    """
    A class representing a rectangle object
    ...
    Attributes
    ----------
    min : Point
        a shapely point object storing the minimum x and y coordinates
    max : Point
        a shapely point object storing the maximum x and y coordinates
    """

    def __init__(self, x1, y1, x2, y2):
        minx, maxx = (x1,x2) if x1 < x2 else (x2,x1)
        miny, maxy = (y1,y2) if y1 < y2 else (y2,y1)
        self.min, self.max = Point(minx, miny), Point(maxx, maxy)

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
    center = Point(rect.min.x + (w / 2), rect.min.y + (h / 2))
    delta_x = plus_or_minus(uniform(0, w / factor))
    delta_y = plus_or_minus(uniform(0, h / factor))
    interior = Point(center.x + delta_x, center.y + delta_y)

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
    """ Return a list of random rectangles across the landscape region (noting that the rectangle sizes are also random) """

    # call quadsect() until at least the number of rects wanted has been generated
    rects = [region]   # seed output list
    while len(rects) <= num_recs_to_generate:
        rects = [subrect for rect in rects
                            for subrect in quadsect(rect, 3)]

    random.shuffle(rects)  # mix them up
    sample = random.sample(rects, num_rectangles)  # select the desired number

    return sample