from tests.isolated_test_case import IsolatedTestCase
import unittest
import time
import sys
import os

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from focuscli import Stopwatch, ThresholdTimer, CountdownTimer

class TestTimers(IsolatedTestCase):

    def test_stopwatch(self):
        s = Stopwatch()
        self.assertFalse(s.is_active)
        self.assertEqual(s.elapsed(), 0)

        s.start()
        self.assertTrue(s.is_active)
        time.sleep(0.1)
        self.assertGreater(s.elapsed(), 0)

        s.stop()
        self.assertFalse(s.is_active)

    def test_threshold_timer(self):
        t = ThresholdTimer(threshold_seconds=1)
        t.start()
        self.assertFalse(t.is_exceeded())
        self.assertLessEqual(t.remaining(), 1)

        # Mocking time for faster tests
        t.start_time = time.time() - 2
        self.assertTrue(t.is_exceeded())
        self.assertLess(t.remaining(), 0)

    def test_countdown_timer(self):
        c = CountdownTimer(duration_seconds=10)
        c.start()
        self.assertEqual(c.remaining_seconds, 10)

        # Mocking tick
        c.last_tick = time.time() - 2
        c.tick()
        self.assertEqual(c.remaining_seconds, 8)

        c.reset(duration_seconds=5)
        self.assertEqual(c.remaining_seconds, 5)

if __name__ == '__main__':
    unittest.main()
