#from https://algorithmtutor.com/Computational-Geometry/Check-if-a-point-is-inside-a-polygon/

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


def is_within_polygon(pts_absolute, location):
    A = []
    B = []
    C = []  

    polygon = [Point(pts_absolute.item(0),pts_absolute.item(1)), Point(pts_absolute.item(2),pts_absolute.item(3)),Point(pts_absolute.item(4),pts_absolute.item(5)),Point(pts_absolute.item(6),pts_absolute.item(7))]
    point = Point(location[0], location[1])

    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % len(polygon)]
        
        # calculate A, B and C
        a = -(p2.y - p1.y)
        b = p2.x - p1.x
        c = -(a * p1.x + b * p1.y)

        A.append(a)
        B.append(b)
        C.append(c)

    D = []
    for i in range(len(A)):
        d = A[i] * point.x + B[i] * point.y + C[i]
        D.append(d)

    t1 = all(d >= 0 for d in D)
    t2 = all(d <= 0 for d in D)
    return t1 or t2
