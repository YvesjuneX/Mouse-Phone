import unittest
from motion import Motion


class MotionTests(unittest.TestCase):
    def setUp(self):
        self.position = (100, 100)
        self.points = []
        self.motion = Motion(lambda: self.position, self.write, (0, 0, 1919, 1079))

    def write(self, x, y):
        self.position = (x, y)
        self.points.append(self.position)

    def settle(self):
        for _ in range(30):
            self.motion.tick(1 / 120)

    def test_monotonic_no_overshoot_or_oscillation(self):
        self.motion.add(120, 60)
        self.settle()
        self.assertEqual(self.position, (220, 160))
        self.assertEqual(self.points, sorted(self.points))
        count = len(self.points)
        self.settle()
        self.assertEqual(len(self.points), count)

    def test_subpixel_packets_survive_idle_ticks(self):
        for _ in range(100):
            self.motion.add(.1, -.1)
            self.settle()
        self.assertEqual(self.position, (110, 90))

    def test_reversal_and_click_flush(self):
        self.motion.add(100, 0)
        self.motion.tick(1 / 120)
        self.motion.add(-150, 0)
        self.motion.tick(0, finish=True)
        self.assertEqual(self.position, (50, 100))

    def test_physical_mouse_is_not_pulled_back(self):
        self.motion.add(100, 0)
        self.position = (700, 500)
        self.settle()
        self.assertEqual(self.position, (700, 500))

    def test_edge_does_not_accumulate_hidden_movement(self):
        self.motion.add(10000, 0)
        self.settle()
        self.motion.add(-10, 0)
        self.settle()
        self.assertEqual(self.position[0], 1909)


if __name__ == '__main__':
    unittest.main()
