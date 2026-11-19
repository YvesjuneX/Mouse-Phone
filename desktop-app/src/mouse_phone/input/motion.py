"""Bounded cursor interpolation; no velocity extrapolation or movement queue."""
import math


class Motion:
    def __init__(self, read, write, bounds):
        self.read, self.write, self.bounds = read, write, bounds
        self.reset()

    def reset(self):
        self.x, self.y = self.read()
        self.tx, self.ty = self.x, self.y
        self.last_written = (self.x, self.y)
        self.active = False

    def add(self, dx, dy):
        if not self.active and self.read() != self.last_written:
            self.reset()
        left, top, right, bottom = self.bounds
        self.tx = min(right, max(left, self.tx + dx))
        self.ty = min(bottom, max(top, self.ty + dy))
        self.active = True

    def tick(self, dt, finish=False):
        if not self.active:
            return
        # Physical mouse input takes priority; do not pull it back to an old target.
        if self.read() != self.last_written:
            self.reset()
            return
        alpha = 1.0 if finish else 1.0 - math.exp(-min(dt, .025) / .008)
        self.x += (self.tx - self.x) * alpha
        self.y += (self.ty - self.y) * alpha
        if max(abs(self.tx - self.x), abs(self.ty - self.y)) < .05:
            self.x, self.y = self.tx, self.ty
            self.active = False
        point = (round(self.x), round(self.y))
        if point != self.last_written:
            self.write(*point)
            self.last_written = self.read()
